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

import {
  analogCurvePresets,
  analogCurveToView,
} from "$lib/configurator/lib/gamepad"
import { gamepadQueryContext } from "$lib/configurator/queries/gamepad-query.svelte"
import { Context } from "runed"

export class AnalogCurveState {
  viewCurve: { x: number; y: number }[] = $state(
    analogCurveToView(analogCurvePresets[0].curve),
  )

  constructor() {
    const analogCurve = $derived(
      gamepadQueryContext.get().gamepadOptions.current?.analogCurve,
    )

    $effect(() => {
      if (analogCurve) {
        this.viewCurve = analogCurveToView(analogCurve)
      }
    })
  }
}

export const analogCurveStateContext = new Context<AnalogCurveState>(
  "hmk-analog-curve-state",
)
