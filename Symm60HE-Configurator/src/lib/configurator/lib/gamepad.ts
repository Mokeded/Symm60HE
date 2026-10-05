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

import { HMK_MAX_DISTANCE, HMK_MIN_DISTANCE } from "$lib/libhmk"
import {
  HMK_GamepadButton,
  type HMK_GamepadAnalogCurve,
} from "$lib/libhmk/gamepad"

export const CURVE_VIEW_WIDTH = 350
export const CURVE_VIEW_HEIGHT = 200

export const gamepadButtons: HMK_GamepadButton[] = [
  HMK_GamepadButton.A,
  HMK_GamepadButton.B,
  HMK_GamepadButton.X,
  HMK_GamepadButton.Y,
  HMK_GamepadButton.START,
  HMK_GamepadButton.BACK,
  HMK_GamepadButton.HOME,
  HMK_GamepadButton.UP,
  HMK_GamepadButton.DOWN,
  HMK_GamepadButton.LEFT,
  HMK_GamepadButton.RIGHT,
  HMK_GamepadButton.LS_UP,
  HMK_GamepadButton.LS_DOWN,
  HMK_GamepadButton.LS_LEFT,
  HMK_GamepadButton.LS_RIGHT,
  HMK_GamepadButton.LS,
  HMK_GamepadButton.RS_UP,
  HMK_GamepadButton.RS_DOWN,
  HMK_GamepadButton.RS_LEFT,
  HMK_GamepadButton.RS_RIGHT,
  HMK_GamepadButton.RS,
  HMK_GamepadButton.LB,
  HMK_GamepadButton.LT,
  HMK_GamepadButton.RB,
  HMK_GamepadButton.RT,
]

export type GamepadAnalogCurvePreset = {
  name: string
  curve: HMK_GamepadAnalogCurve
}

export const analogCurvePresets: GamepadAnalogCurvePreset[] = [
  {
    name: "Linear",
    curve: [
      { x: 4, y: 20 },
      { x: 85, y: 95 },
      { x: 165, y: 170 },
      { x: 255, y: 255 },
    ],
  },
  {
    name: "Aggressive",
    curve: [
      { x: 4, y: 20 },
      { x: 55, y: 150 },
      { x: 145, y: 220 },
      { x: 255, y: 255 },
    ],
  },
  {
    name: "Slow",
    curve: [
      { x: 4, y: 20 },
      { x: 105, y: 55 },
      { x: 205, y: 120 },
      { x: 255, y: 255 },
    ],
  },
  {
    name: "Smooth",
    curve: [
      { x: 4, y: 20 },
      { x: 95, y: 80 },
      { x: 185, y: 160 },
      { x: 255, y: 255 },
    ],
  },
  {
    name: "Step",
    curve: [
      { x: 4, y: 20 },
      { x: 37, y: 130 },
      { x: 195, y: 130 },
      { x: 255, y: 255 },
    ],
  },
  {
    name: "Instant",
    curve: [
      { x: 4, y: 255 },
      { x: 5, y: 255 },
      { x: 6, y: 255 },
      { x: 255, y: 255 },
    ],
  },
  {
    name: "Digital",
    curve: [
      { x: 4, y: 255 },
      { x: 5, y: 255 },
      { x: 6, y: 255 },
      { x: 7, y: 255 },
    ],
  },
]

export function analogCurveToView(v: HMK_GamepadAnalogCurve) {
  return v.map(({ x, y }) => ({
    x:
      ((x - HMK_MIN_DISTANCE) * CURVE_VIEW_WIDTH) /
      (HMK_MAX_DISTANCE - HMK_MIN_DISTANCE),
    y: CURVE_VIEW_HEIGHT - (y * CURVE_VIEW_HEIGHT) / 255,
  }))
}

export function viewCurveToAnalog(v: HMK_GamepadAnalogCurve) {
  return v.map(({ x, y }) => ({
    x:
      Math.round(
        (x * (HMK_MAX_DISTANCE - HMK_MIN_DISTANCE)) / CURVE_VIEW_WIDTH,
      ) + HMK_MIN_DISTANCE,
    y: Math.round((255 * (CURVE_VIEW_HEIGHT - y)) / CURVE_VIEW_HEIGHT),
  }))
}
