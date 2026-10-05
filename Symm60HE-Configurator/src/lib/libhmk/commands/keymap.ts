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
import type { GetKeymapParams, SetKeymapParams } from "$lib/keyboard"
import type { Commander } from "$lib/keyboard/commander"
import type { KeyboardMetadata } from "$lib/keyboard/metadata"
import { HMK_Command } from "."

const GET_KEYMAP_MAX_ENTRIES = 63

export async function getKeymap(
  commander: Commander,
  { numLayers, numKeys }: KeyboardMetadata,
  { profile }: GetKeymapParams,
) {
  const ret: number[][] = []
  for (let layer = 0; layer < numLayers; layer++) {
    const currentLayer: number[] = []
    for (let i = 0; i < numKeys; i += GET_KEYMAP_MAX_ENTRIES) {
      const reader = new DataViewReader(
        await commander.sendCommand({
          command: HMK_Command.GET_KEYMAP,
          payload: [profile, layer, i],
        }),
      )

      for (let j = 0; j < GET_KEYMAP_MAX_ENTRIES && i + j < numKeys; j++) {
        currentLayer.push(reader.uint8())
      }
    }
    ret.push(currentLayer)
  }

  return ret
}

const SET_KEYMAP_MAX_ENTRIES = 59

export async function setKeymap(
  commander: Commander,
  { profile, layer, offset, data }: SetKeymapParams,
) {
  for (let i = 0; i < data.length; i += SET_KEYMAP_MAX_ENTRIES) {
    const part = data.slice(i, i + SET_KEYMAP_MAX_ENTRIES)
    await commander.sendCommand({
      command: HMK_Command.SET_KEYMAP,
      payload: [profile, layer, offset + i, part.length, ...part],
    })
  }
}
