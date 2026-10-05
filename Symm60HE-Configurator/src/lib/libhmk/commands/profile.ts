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
import type { DuplicateProfileParams, ResetProfileParams } from "$lib/keyboard"
import type { Commander } from "$lib/keyboard/commander"
import { HMK_Command } from "."

export async function getProfile(commander: Commander) {
  return new DataViewReader(
    await commander.sendCommand({ command: HMK_Command.GET_PROFILE }),
  ).uint8()
}

export async function resetProfile(
  commander: Commander,
  { profile }: ResetProfileParams,
) {
  await commander.sendCommand({
    command: HMK_Command.RESET_PROFILE,
    payload: [profile],
  })
}

export async function duplicateProfile(
  commander: Commander,
  { profile, srcProfile }: DuplicateProfileParams,
) {
  await commander.sendCommand({
    command: HMK_Command.DUPLICATE_PROFILE,
    payload: [profile, srcProfile],
  })
}
