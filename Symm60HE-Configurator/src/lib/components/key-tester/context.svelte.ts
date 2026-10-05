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

import { Context, useEventListener } from "runed"

const KEY_UP_TIMEOUT = 750

export class KeyTesterState {
  keyEvents: {
    webCode: string
    display: string
    pressed: boolean
  }[] = $state([])

  constructor() {
    useEventListener(
      () => document.body,
      "keydown",
      (e) =>
        !e.repeat &&
        this.keyEvents.push({
          webCode: e.code,
          display: e.code === "" ? e.key : e.code,
          pressed: true,
        }),
    )
    useEventListener(
      () => document.body,
      "keyup",
      (e) => {
        const index = this.keyEvents.findIndex(
          ({ webCode, pressed }) => webCode === e.code && pressed,
        )
        if (index !== -1) {
          this.keyEvents[index].pressed = false
        }
        setTimeout(() => {
          const index = this.keyEvents.findIndex(
            ({ webCode, pressed }) => webCode === e.code && !pressed,
          )
          if (index !== -1) {
            this.keyEvents.splice(index, 1)
          }
        }, KEY_UP_TIMEOUT)
      },
    )
    useEventListener(
      () => window,
      "blur",
      () => (this.keyEvents.length = 0),
    )
  }
}

export const keyTesterStateContext = new Context<KeyTesterState>(
  "hmk-key-tester-state",
)
