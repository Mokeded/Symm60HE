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
  GetGamepadOptionsParams,
  SetGamepadOptionsParams,
} from "$lib/keyboard"
import type { Commander } from "$lib/keyboard/commander"
import { HMK_Command } from "."
import type { HMK_GamepadOptions } from "../gamepad"

export async function getGamepadOptions(
  commander: Commander,
  { profile }: GetGamepadOptionsParams,
): Promise<HMK_GamepadOptions> {
  const reader = new DataViewReader(
    await commander.sendCommand({
      command: HMK_Command.GET_GAMEPAD_OPTIONS,
      payload: [profile],
    }),
  )

  const analogCurve = [...Array(4)].map(() => ({
    x: reader.uint8(),
    y: reader.uint8(),
  }))
  const optionsRaw = reader.uint8()

  return {
    analogCurve,
    keyboardEnabled: ((optionsRaw >> 0) & 1) !== 0,
    gamepadOverride: ((optionsRaw >> 1) & 1) !== 0,
    squareJoystick: ((optionsRaw >> 2) & 1) !== 0,
    snappyJoystick: ((optionsRaw >> 3) & 1) !== 0,
  }
}

export async function setGamepadOptions(
  commander: Commander,
  {
    profile,
    data: {
      analogCurve,
      keyboardEnabled,
      gamepadOverride,
      squareJoystick,
      snappyJoystick,
    },
  }: SetGamepadOptionsParams,
) {
  await commander.sendCommand({
    command: HMK_Command.SET_GAMEPAD_OPTIONS,
    payload: [
      profile,
      ...analogCurve.flatMap(({ x, y }) => [x, y]),
      ((keyboardEnabled ? 1 : 0) << 0) |
        ((gamepadOverride ? 1 : 0) << 1) |
        ((squareJoystick ? 1 : 0) << 2) |
        ((snappyJoystick ? 1 : 0) << 3),
    ],
  })
}
