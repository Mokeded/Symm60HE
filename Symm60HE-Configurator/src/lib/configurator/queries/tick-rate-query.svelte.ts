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

import { keyboardContext, type SetTickRateParams } from "$lib/keyboard"
import { Context, resource, type ResourceReturn } from "runed"
import { optimisticUpdate } from "."
import { globalStateContext } from "../context.svelte"

export class TickRateQuery {
  tickRate: ResourceReturn<number>

  #keyboard = keyboardContext.get()
  #profile = $derived(globalStateContext.get().profile)

  constructor() {
    this.tickRate = resource(
      () => ({ profile: this.#profile }),
      (p) => this.#keyboard.getTickRate(p),
    )
  }

  async set(params: Omit<SetTickRateParams, "profile">) {
    const { data } = params
    await optimisticUpdate({
      resource: this.tickRate,
      optimisticFn: () => data,
      updateFn: () =>
        this.#keyboard.setTickRate({ ...params, profile: this.#profile }),
    })
  }
}

export const tickRateQueryContext = new Context<TickRateQuery>(
  "hmk-tick-rate-query",
)
