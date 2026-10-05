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

import { uint8Schema } from "$lib/integer"
import z from "zod"

export enum HMK_GamepadButton {
  NONE = 0,

  // Digital buttons
  A,
  B,
  X,
  Y,
  UP,
  DOWN,
  LEFT,
  RIGHT,
  START,
  BACK,
  HOME,
  LS,
  RS,
  LB,
  RB,

  // Analog buttons
  LS_UP,
  LS_DOWN,
  LS_LEFT,
  LS_RIGHT,
  RS_UP,
  RS_DOWN,
  RS_LEFT,
  RS_RIGHT,
  LT,
  RT,
}

export const hmkGamepadAnalogCurveSchema = z
  .array(z.object({ x: uint8Schema, y: uint8Schema }))
  .length(4)

export type HMK_GamepadAnalogCurve = z.infer<typeof hmkGamepadAnalogCurveSchema>

export const hmkGamepadOptionsSchema = z.object({
  analogCurve: hmkGamepadAnalogCurveSchema,
  keyboardEnabled: z.boolean(),
  gamepadOverride: z.boolean(),
  squareJoystick: z.boolean(),
  snappyJoystick: z.boolean(),
})

export type HMK_GamepadOptions = z.infer<typeof hmkGamepadOptionsSchema>
