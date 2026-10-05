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

import { DataViewReader } from "$lib/data-view-reader"
import type {
  GetGamepadButtonsParams,
  SetGamepadButtonsParams,
} from "$lib/keyboard"
import type { Commander } from "$lib/keyboard/commander"
import type { KeyboardMetadata } from "$lib/keyboard/metadata"
import { HMK_Command } from "."

const GET_GAMEPAD_BUTTONS_MAX_ENTRIES = 63

export async function getGamepadButtons(
  commander: Commander,
  { numKeys }: KeyboardMetadata,
  { profile }: GetGamepadButtonsParams,
) {
  const ret: number[] = []
  for (let i = 0; i < numKeys; i += GET_GAMEPAD_BUTTONS_MAX_ENTRIES) {
    const reader = new DataViewReader(
      await commander.sendCommand({
        command: HMK_Command.GET_GAMEPAD_BUTTONS,
        payload: [profile, i],
      }),
    )

    for (
      let j = 0;
      j < GET_GAMEPAD_BUTTONS_MAX_ENTRIES && i + j < numKeys;
      j++
    ) {
      ret.push(reader.uint8())
    }
  }

  return ret
}

const SET_GAMEPAD_BUTTONS_MAX_ENTRIES = 59

export async function setGamepadButtons(
  commander: Commander,
  { profile, offset, data }: SetGamepadButtonsParams,
) {
  for (let i = 0; i < data.length; i += SET_GAMEPAD_BUTTONS_MAX_ENTRIES) {
    const part = data.slice(i, i + SET_GAMEPAD_BUTTONS_MAX_ENTRIES)
    await commander.sendCommand({
      command: HMK_Command.SET_GAMEPAD_BUTTONS,
      payload: [profile, offset + i, part.length, ...part],
    })
  }
}
