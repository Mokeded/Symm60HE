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

import { keyboardContext, type SetAdvancedKeysParams } from "$lib/keyboard"
import type { HMK_AdvancedKey } from "$lib/libhmk/advanced-keys"
import { Context, resource, type ResourceReturn } from "runed"
import { optimisticUpdate } from "."
import { globalStateContext } from "../context.svelte"

export class AdvancedKeysQuery {
  advancedKeys: ResourceReturn<HMK_AdvancedKey[]>
  display?: { count: number; indices: (number | null)[][] }

  #keyboard = keyboardContext.get()
  #profile = $derived(globalStateContext.get().profile)

  constructor() {
    this.advancedKeys = resource(
      () => ({ profile: this.#profile }),
      (p) => this.#keyboard.getAdvancedKeys(p),
    )
  }

  async set(params: Omit<SetAdvancedKeysParams, "profile">) {
    const { offset, data } = params
    await optimisticUpdate({
      resource: this.advancedKeys,
      optimisticFn: (current) => {
        const ret = [...current]
        for (let i = 0; i < data.length; i++) {
          ret[offset + i] = data[i]
        }
        return ret
      },
      updateFn: () =>
        this.#keyboard.setAdvancedKeys({ ...params, profile: this.#profile }),
    })
  }
}

export const advancedKeysQueryContext = new Context<AdvancedKeysQuery>(
  "hmk-advanced-keys-query",
)
