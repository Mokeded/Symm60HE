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

#pragma once

#include "common.h"

//--------------------------------------------------------------------+
// Deferred Actions
//--------------------------------------------------------------------+

#if !defined(MAX_DEFERRED_ACTIONS)
// Maximum number of deferred actions for each matrix scan
#define MAX_DEFERRED_ACTIONS 16
#endif

_Static_assert(M_IS_POWER_OF_TWO(MAX_DEFERRED_ACTIONS),
               "MAX_DEFERRED_ACTIONS must be a power of two");

// Deferred action type
typedef enum {
  DEFERRED_ACTION_TYPE_NONE = 0,
  DEFERRED_ACTION_TYPE_PRESS,
  DEFERRED_ACTION_TYPE_RELEASE,
  DEFERRED_ACTION_TYPE_TAP,
  DEFERRED_ACTION_TYPE_COUNT,
} deferred_action_type_t;

// Deferred action. The action will be deferred to the next matrix scan. This is
// necessary to implement features like tapping keys and DKS.
typedef struct {
  // Action to perform
  uint8_t type;
  // Key index
  uint8_t key;
  // Keycode associated with the action
  uint8_t keycode;
  // Number of matrix scans to wait before executing the action
  uint8_t ticks;
} deferred_action_t;

//--------------------------------------------------------------------+
// Deferred Action API
//--------------------------------------------------------------------+

/**
 * @brief Initialize the deferred action module
 *
 * @return None
 */
void deferred_action_init(void);

/**
 * @brief Push a deferred action to the stack
 *
 * The action may not be pushed if the stack is locked or full. The stack is
 * locked if it is being processed.
 *
 * @param action Deferred action
 *
 * @return true if the action was pushed, false otherwise
 */
bool deferred_action_push(const deferred_action_t *action);

/**
 * @brief Process all deferred actions and clear the stack
 *
 * @return None
 */
void deferred_action_process(void);
