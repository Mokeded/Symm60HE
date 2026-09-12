/*
 * This program is free software: you can redistribute it and/or modify it under
 * the terms of the GNU General Public License as published by the Free Software
 * Foundation, either version 3 of the License, or (at your option) any later
 * version.
 *
 * This program is distributed in the hope that it will be useful, but WITHOUT
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
 * FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
 * details.
 *
 * You should have received a copy of the GNU General Public License along with
 * this program. If not, see <https://www.gnu.org/licenses/>.
 */

#include "deferred_actions.h"

#include "eeconfig.h"
#include "layout.h"

// Lock for the deferred action queue
static bool queue_lock;

// Deferred action queue
static uint32_t queue_head;
static uint32_t queue_size;
static deferred_action_t queue[MAX_DEFERRED_ACTIONS];

static void deferred_action_execute(const deferred_action_t *action) {
  static deferred_action_t deferred_action = {0};

  switch (action->type) {
  case DEFERRED_ACTION_TYPE_PRESS:
    layout_register(action->key, action->keycode);
    break;

  case DEFERRED_ACTION_TYPE_RELEASE:
    layout_unregister(action->key, action->keycode);
    break;

  case DEFERRED_ACTION_TYPE_TAP:
    deferred_action = (deferred_action_t){
        .type = DEFERRED_ACTION_TYPE_RELEASE,
        .key = action->key,
        .keycode = action->keycode,
    };
    if (deferred_action_push(&deferred_action))
      // We only perform the tap action if the release action was successfully
      // enqueued. Otherwise, the key will be stuck in the pressed state.
      layout_register(action->key, action->keycode);
    break;

  default:
    break;
  }
}

void deferred_action_init(void) {}

bool deferred_action_push(const deferred_action_t *action) {
  if (queue_lock || queue_size == MAX_DEFERRED_ACTIONS)
    return false;

  queue_lock = true;

  deferred_action_t *queue_tail =
      &queue[(queue_head + queue_size) & (MAX_DEFERRED_ACTIONS - 1)];
  queue_size++;
  *queue_tail = *action;
  queue_tail->ticks = CURRENT_PROFILE.tick_rate;

  queue_lock = false;

  return true;
}

void deferred_action_process(void) {
  static deferred_action_t buffer[MAX_DEFERRED_ACTIONS];

  if (queue_lock || queue_size == 0)
    return;

  queue_lock = true;

  // Copy actions in the queue to a buffer to avoid the queue being locked while
  // executing those actions
  uint32_t action_count = 0;
  for (uint32_t i = 0; i < queue_size; i++) {
    deferred_action_t *action =
        &queue[(queue_head + i) & (MAX_DEFERRED_ACTIONS - 1)];

    // Make sure the ticks are not greater than the tick rate
    action->ticks = M_MIN(action->ticks, CURRENT_PROFILE.tick_rate);
    if (action->ticks > 0) {
      // Decrement the ticks and skip the action if it is not ready yet
      action->ticks--;
      continue;
    }
    buffer[action_count++] = *action;
  }
  // Move the head of the queue forward by the number of actions processed
  queue_head = (queue_head + action_count) & (MAX_DEFERRED_ACTIONS - 1);
  queue_size -= action_count;

  queue_lock = false;

  // Execute all the actions
  for (uint32_t i = 0; i < action_count; i++)
    deferred_action_execute(&buffer[i]);
}
