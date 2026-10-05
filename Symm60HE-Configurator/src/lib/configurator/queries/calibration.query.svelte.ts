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

import { keyboardContext, type SetCalibrationParams } from "$lib/keyboard"
import type { HMK_Calibration } from "$lib/libhmk"
import { Context, resource, type ResourceReturn } from "runed"
import { optimisticUpdate } from "."

export class CalibrationQuery {
  calibration: ResourceReturn<HMK_Calibration>

  #keyboard = keyboardContext.get()

  constructor() {
    this.calibration = resource(
      () => {},
      () => this.#keyboard.getCalibration(),
    )
  }

  async set(params: SetCalibrationParams) {
    const { data } = params
    await optimisticUpdate({
      resource: this.calibration,
      optimisticFn: () => data,
      updateFn: () => this.#keyboard.setCalibration(params),
    })
  }
}

export const calibrationQueryContext = new Context<CalibrationQuery>(
  "hmk-calibration-query",
)
