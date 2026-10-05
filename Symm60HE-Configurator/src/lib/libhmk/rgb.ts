/*
 * This program is free software: you can redistribute it and/or modify it under
 * the terms of the GNU General Public License as published by the Free Software
 * Foundation, either version 3 of the License, or (at your option) any later
 * version.
 */

export enum HMK_RGBEffect {
  SOLID = 0,
  BREATHING,
  RAINBOW,
  WAVE,
}

export type HMK_RGBConfig = {
  enabled: boolean
  effect: HMK_RGBEffect
  brightness: number
  speed: number
  red: number
  green: number
  blue: number
  splitMirror: boolean
}

export const HMK_RGB_EFFECT_NAMES: Record<HMK_RGBEffect, string> = {
  [HMK_RGBEffect.SOLID]: "Solid",
  [HMK_RGBEffect.BREATHING]: "Breathing",
  [HMK_RGBEffect.RAINBOW]: "Rainbow",
  [HMK_RGBEffect.WAVE]: "Wave",
}
