/*
 * This program is free software: you can redistribute it and/or modify it under
 * the terms of the GNU General Public License as published by the Free Software
 * Foundation, either version 3 of the License, or (at your option) any later
 * version.
 */

import { keyboardContext, type SetRGBConfigParams } from "$lib/keyboard"
import type { HMK_RGBConfig } from "$lib/libhmk/rgb"
import { Context, resource, type ResourceReturn } from "runed"
import { optimisticUpdate } from "."

export class RGBQuery {
  config: ResourceReturn<HMK_RGBConfig>

  #keyboard = keyboardContext.get()

  constructor() {
    this.config = resource(
      () => {},
      () => this.#keyboard.getRGBConfig(),
    )
  }

  async set(params: SetRGBConfigParams) {
    const { data } = params
    await optimisticUpdate({
      resource: this.config,
      optimisticFn: () => data,
      updateFn: () => this.#keyboard.setRGBConfig(params),
    })
  }
}

export const rgbQueryContext = new Context<RGBQuery>("hmk-rgb-query")
