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

import { keyboardContext, type SetKeymapParams } from "$lib/keyboard"
import { Context, resource, type ResourceReturn } from "runed"
import { optimisticUpdate } from "."
import { globalStateContext } from "../context.svelte"

export class KeymapQuery {
  keymap: ResourceReturn<number[][]>

  #keyboard = keyboardContext.get()
  #profile = $derived(globalStateContext.get().profile)

  constructor() {
    this.keymap = resource(
      () => ({ profile: this.#profile }),
      (p) => this.#keyboard.getKeymap(p),
    )
  }

  async set(params: Omit<SetKeymapParams, "profile">) {
    const { layer, offset, data } = params
    await optimisticUpdate({
      resource: this.keymap,
      optimisticFn: (current) => {
        const ret = current.map((row) => [...row])
        for (let i = 0; i < data.length; i++) {
          ret[layer][offset + i] = data[i]
        }
        return ret
      },
      updateFn: () =>
        this.#keyboard.setKeymap({ ...params, profile: this.#profile }),
    })
  }
}

export const keymapQueryContext = new Context<KeymapQuery>("hmk-keymap-query")
