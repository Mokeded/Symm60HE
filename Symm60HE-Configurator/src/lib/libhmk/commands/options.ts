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
import type { SetOptionsParams } from "$lib/keyboard"
import type { Commander } from "$lib/keyboard/commander"
import { HMK_Command } from "."
import type { HMK_Options } from ".."

export async function getOptions(commander: Commander): Promise<HMK_Options> {
  const optionsRaw = new DataViewReader(
    await commander.sendCommand({ command: HMK_Command.GET_OPTIONS }),
  ).uint16()

  return {
    xInputEnabled: ((optionsRaw >> 0) & 1) !== 0,
    saveBottomOutThreshold: ((optionsRaw >> 1) & 1) !== 0,
    highPollingRateEnabled: ((optionsRaw >> 2) & 1) !== 0,
  }
}

export async function setOptions(
  commander: Commander,
  {
    data: { xInputEnabled, saveBottomOutThreshold, highPollingRateEnabled },
  }: SetOptionsParams,
) {
  await commander.sendCommand({
    command: HMK_Command.SET_OPTIONS,
    payload: [
      ((xInputEnabled ? 1 : 0) << 0) |
        ((saveBottomOutThreshold ? 1 : 0) << 1) |
        ((highPollingRateEnabled ? 1 : 0) << 2),
    ],
  })
}
