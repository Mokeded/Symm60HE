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

import { keyboardContext } from "$lib/keyboard"
import type { HMK_AnalogInfo } from "$lib/libhmk/commands"
import { Context, resource, type ResourceReturn } from "runed"

const ANALOG_INFO_REFETCH_INTERVAL = 1000 / 30

export class AnalogInfoQuery {
  analogInfo: ResourceReturn<HMK_AnalogInfo[]>
  enabled = $state(false)

  #keyboard = keyboardContext.get()

  constructor() {
    this.analogInfo = resource(
      () => this.enabled,
      async (enabled) => {
        if (!enabled) return this.analogInfo.current
        const ret = await this.#keyboard.analogInfo()
        setTimeout(
          () => this.analogInfo.refetch(),
          ANALOG_INFO_REFETCH_INTERVAL,
        )
        return ret
      },
      { lazy: true },
    )
  }

  async recalibrate() {
    try {
      await this.#keyboard.recalibrate()
    } catch (err) {
      console.error(err)
    } finally {
      this.analogInfo.refetch()
    }
  }
}

export const analogInfoQueryContext = new Context<AnalogInfoQuery>(
  "hmk-analog-info-query",
)
