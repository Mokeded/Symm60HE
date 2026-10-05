/*
 * This program is free software: you can redistribute it and/or modify it under
 * the terms of the GNU General Public License as published by the Free Software
 * Foundation, either version 3 of the License, or (at your option) any later
 * version.
 */

import { DataViewReader } from "$lib/data-view-reader"
import type { SetRGBConfigParams } from "$lib/keyboard"
import type { Commander } from "$lib/keyboard/commander"
import { HMK_Command } from "."
import { HMK_RGBEffect, type HMK_RGBConfig } from "../rgb"

export async function getRGBConfig(
  commander: Commander,
): Promise<HMK_RGBConfig> {
  const reader = new DataViewReader(
    await commander.sendCommand({ command: HMK_Command.GET_RGB_CONFIG }),
  )

  const enabled = reader.uint8() !== 0
  const effect = reader.uint8()
  if (effect < HMK_RGBEffect.SOLID || effect > HMK_RGBEffect.WAVE) {
    throw new Error(`Unknown RGB effect ${effect}`)
  }

  return {
    enabled,
    effect,
    brightness: reader.uint8(),
    speed: reader.uint8(),
    red: reader.uint8(),
    green: reader.uint8(),
    blue: reader.uint8(),
    splitMirror: reader.uint8() !== 0,
  }
}

export async function setRGBConfig(
  commander: Commander,
  { data }: SetRGBConfigParams,
) {
  await commander.sendCommand({
    command: HMK_Command.SET_RGB_CONFIG,
    payload: [
      data.enabled ? 1 : 0,
      data.effect,
      data.brightness,
      data.speed,
      data.red,
      data.green,
      data.blue,
      data.splitMirror ? 1 : 0,
    ],
  })
}
