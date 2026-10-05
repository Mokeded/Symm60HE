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
  GetActuationMapParams,
  SetActuationMapParams,
} from "$lib/keyboard"
import type { Commander } from "$lib/keyboard/commander"
import type { KeyboardMetadata } from "$lib/keyboard/metadata"
import { HMK_Command } from "."
import type { HMK_Actuation } from "../actuation"

const GET_ACTUATION_MAP_MAX_ENTRIES = 15

export async function getActuationMap(
  commander: Commander,
  { numKeys }: KeyboardMetadata,
  { profile }: GetActuationMapParams,
) {
  const ret: HMK_Actuation[] = []
  for (let i = 0; i < numKeys; i += GET_ACTUATION_MAP_MAX_ENTRIES) {
    const reader = new DataViewReader(
      await commander.sendCommand({
        command: HMK_Command.GET_ACTUATION_MAP,
        payload: [profile, i],
      }),
    )

    for (let j = 0; j < GET_ACTUATION_MAP_MAX_ENTRIES && i + j < numKeys; j++) {
      ret.push({
        actuationPoint: reader.uint8(),
        rtDown: reader.uint8(),
        rtUp: reader.uint8(),
        continuous: reader.uint8() !== 0,
      })
    }
  }

  return ret
}

const SET_ACTUATION_MAP_MAX_ENTRIES = 15

export async function setActuationMap(
  commander: Commander,
  { profile, offset, data }: SetActuationMapParams,
) {
  for (let i = 0; i < data.length; i += SET_ACTUATION_MAP_MAX_ENTRIES) {
    const part = data.slice(i, i + SET_ACTUATION_MAP_MAX_ENTRIES)
    await commander.sendCommand({
      command: HMK_Command.SET_ACTUATION_MAP,
      payload: [
        profile,
        offset + i,
        part.length,
        ...part.flatMap(({ actuationPoint, rtDown, rtUp, continuous }) => [
          actuationPoint,
          rtDown,
          rtUp,
          continuous ? 1 : 0,
        ]),
      ],
    })
  }
}
