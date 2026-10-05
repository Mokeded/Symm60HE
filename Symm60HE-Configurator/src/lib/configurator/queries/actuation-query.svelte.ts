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

import { keyboardContext, type SetActuationMapParams } from "$lib/keyboard"
import type { HMK_Actuation } from "$lib/libhmk/actuation"
import { Context, resource, type ResourceReturn } from "runed"
import { optimisticUpdate } from "."
import { globalStateContext } from "../context.svelte"

export class ActuationQuery {
  actuationMap: ResourceReturn<HMK_Actuation[]>

  #keyboard = keyboardContext.get()
  #profile = $derived(globalStateContext.get().profile)

  constructor() {
    this.actuationMap = resource(
      () => ({ profile: this.#profile }),
      (p) => this.#keyboard.getActuationMap(p),
    )
  }

  async set(params: Omit<SetActuationMapParams, "profile">) {
    const { offset, data } = params
    await optimisticUpdate({
      resource: this.actuationMap,
      optimisticFn: (current) => {
        const ret = [...current]
        for (let i = 0; i < data.length; i++) {
          ret[offset + i] = data[i]
        }
        return ret
      },
      updateFn: () =>
        this.#keyboard.setActuationMap({ ...params, profile: this.#profile }),
    })
  }
}

export const actuationQueryContext = new Context<ActuationQuery>(
  "hmk-actuation-query",
)
