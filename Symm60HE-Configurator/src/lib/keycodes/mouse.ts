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

import { Keycode } from "$lib/libhmk/keycodes"
import type { KeycodeMetadata } from "."

export const mouseKeycodeMetadata: KeycodeMetadata[] = [
  {
    name: "Mouse\nL",
    tooltip: "Mouse Button Left",
    keycode: Keycode.SP_MOUSE_BUTTON_1,
    webCodes: [],
    category: "Mouse",
  },
  {
    name: "Mouse\nR",
    tooltip: "Mouse Button Right",
    keycode: Keycode.SP_MOUSE_BUTTON_2,
    webCodes: [],
    category: "Mouse",
  },
  {
    name: "Mouse\nM",
    tooltip: "Mouse Button Middle",
    keycode: Keycode.SP_MOUSE_BUTTON_3,
    webCodes: [],
    category: "Mouse",
  },
  {
    name: "Mouse\n4",
    tooltip: "Mouse Button 4",
    keycode: Keycode.SP_MOUSE_BUTTON_4,
    webCodes: [],
    category: "Mouse",
  },
  {
    name: "Mouse\n5",
    tooltip: "Mouse Button 5",
    keycode: Keycode.SP_MOUSE_BUTTON_5,
    webCodes: [],
    category: "Mouse",
  },
]

export const mouseKeycodes = [
  Keycode.SP_MOUSE_BUTTON_1,
  Keycode.SP_MOUSE_BUTTON_2,
  Keycode.SP_MOUSE_BUTTON_3,
  Keycode.SP_MOUSE_BUTTON_4,
  Keycode.SP_MOUSE_BUTTON_5,
]
