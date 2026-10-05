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

import {
  ArrowDownIcon,
  ArrowLeftIcon,
  ArrowRightIcon,
  ArrowUpIcon,
  CrossIcon,
  Gamepad2Icon,
  MenuIcon,
  StepBackIcon,
  StepForwardIcon,
} from "@lucide/svelte"
import { HMK_GamepadButton } from "$lib/libhmk/gamepad"
import { Keycode } from "$lib/libhmk/keycodes"
import type { KeycodeMetadata } from ".."
import LeftJoystickIcon from "./left-joystick-icon.svelte"
import RightJoystickIcon from "./right-joystick-icon.svelte"

export const gamepadKeycodeMetadata: KeycodeMetadata[] = [
  {
    name: "Gamepad Button A",
    tooltip: "Gamepad Button A",
    display: [Gamepad2Icon, "A"],
    keycode: Keycode.GP_BUTTON_A,
    webCodes: [],
    category: "Gamepad",
  },
  {
    name: "Gamepad Button B",
    tooltip: "Gamepad Button B",
    display: [Gamepad2Icon, "B"],
    keycode: Keycode.GP_BUTTON_B,
    webCodes: [],
    category: "Gamepad",
  },
  {
    name: "Gamepad Button X",
    tooltip: "Gamepad Button X",
    display: [Gamepad2Icon, "X"],
    keycode: Keycode.GP_BUTTON_X,
    webCodes: [],
    category: "Gamepad",
  },
  {
    name: "Gamepad Button Y",
    tooltip: "Gamepad Button Y",
    display: [Gamepad2Icon, "Y"],
    keycode: Keycode.GP_BUTTON_Y,
    webCodes: [],
    category: "Gamepad",
  },
  {
    name: "Gamepad Arrow Up",
    tooltip: "Gamepad Arrow Up",
    display: [CrossIcon, ArrowUpIcon],
    keycode: Keycode.GP_BUTTON_UP,
    webCodes: [],
    category: "Gamepad",
  },
  {
    name: "Gamepad Arrow Down",
    tooltip: "Gamepad Arrow Down",
    display: [CrossIcon, ArrowDownIcon],
    keycode: Keycode.GP_BUTTON_DOWN,
    webCodes: [],
    category: "Gamepad",
  },
  {
    name: "Gamepad Arrow Left",
    tooltip: "Gamepad Arrow Left",
    display: [CrossIcon, ArrowLeftIcon],
    keycode: Keycode.GP_BUTTON_LEFT,
    webCodes: [],
    category: "Gamepad",
  },
  {
    name: "Gamepad Arrow Right",
    tooltip: "Gamepad Arrow Right",
    display: [CrossIcon, ArrowRightIcon],
    keycode: Keycode.GP_BUTTON_RIGHT,
    webCodes: [],
    category: "Gamepad",
  },
  {
    name: "Gamepad Start",
    tooltip: "Gamepad Start",
    display: [Gamepad2Icon, StepForwardIcon],
    keycode: Keycode.GP_BUTTON_START,
    webCodes: [],
    category: "Gamepad",
  },
  {
    name: "Gamepad Select",
    tooltip: "Gamepad Select",
    display: [Gamepad2Icon, StepBackIcon],
    keycode: Keycode.GP_BUTTON_BACK,
    webCodes: [],
    category: "Gamepad",
  },
  {
    name: "Gamepad Home",
    tooltip: "Gamepad Home",
    display: [Gamepad2Icon, MenuIcon],
    keycode: Keycode.GP_BUTTON_HOME,
    webCodes: [],
    category: "Gamepad",
  },
  {
    name: "Gamepad Left Stick",
    tooltip: "Gamepad Left Stick Press",
    display: [LeftJoystickIcon, "Press"],
    keycode: Keycode.GP_BUTTON_LS,
    webCodes: [],
    category: "Gamepad",
  },
  {
    name: "Gamepad Right Stick",
    tooltip: "Gamepad Right Stick Press",
    display: [RightJoystickIcon, "Press"],
    keycode: Keycode.GP_BUTTON_RS,
    webCodes: [],
    category: "Gamepad",
  },
  {
    name: "Gamepad Left Bumper",
    tooltip: "Gamepad Left Bumper",
    display: [Gamepad2Icon, "LB"],
    keycode: Keycode.GP_BUTTON_LB,
    webCodes: [],
    category: "Gamepad",
  },
  {
    name: "Gamepad Right Bumper",
    tooltip: "Gamepad Right Bumper",
    display: [Gamepad2Icon, "RB"],
    keycode: Keycode.GP_BUTTON_RB,
    webCodes: [],
    category: "Gamepad",
  },
  {
    name: "Gamepad Left Stick Up",
    tooltip: "Gamepad Left Stick Up",
    display: [LeftJoystickIcon, ArrowUpIcon],
    keycode: Keycode.GP_BUTTON_LS_UP,
    webCodes: [],
    category: "Gamepad",
  },
  {
    name: "Gamepad Left Stick Down",
    tooltip: "Gamepad Left Stick Down",
    display: [LeftJoystickIcon, ArrowDownIcon],
    keycode: Keycode.GP_BUTTON_LS_DOWN,
    webCodes: [],
    category: "Gamepad",
  },
  {
    name: "Gamepad Left Stick Left",
    tooltip: "Gamepad Left Stick Left",
    display: [LeftJoystickIcon, ArrowLeftIcon],
    keycode: Keycode.GP_BUTTON_LS_LEFT,
    webCodes: [],
    category: "Gamepad",
  },
  {
    name: "Gamepad Left Stick Right",
    tooltip: "Gamepad Left Stick Right",
    display: [LeftJoystickIcon, ArrowRightIcon],
    keycode: Keycode.GP_BUTTON_LS_RIGHT,
    webCodes: [],
    category: "Gamepad",
  },
  {
    name: "Gamepad Right Stick Up",
    tooltip: "Gamepad Right Stick Up",
    display: [RightJoystickIcon, ArrowUpIcon],
    keycode: Keycode.GP_BUTTON_RS_UP,
    webCodes: [],
    category: "Gamepad",
  },
  {
    name: "Gamepad Right Stick Down",
    tooltip: "Gamepad Right Stick Down",
    display: [RightJoystickIcon, ArrowDownIcon],
    keycode: Keycode.GP_BUTTON_RS_DOWN,
    webCodes: [],
    category: "Gamepad",
  },
  {
    name: "Gamepad Right Stick Left",
    tooltip: "Gamepad Right Stick Left",
    display: [RightJoystickIcon, ArrowLeftIcon],
    keycode: Keycode.GP_BUTTON_RS_LEFT,
    webCodes: [],
    category: "Gamepad",
  },
  {
    name: "Gamepad Right Stick Right",
    tooltip: "Gamepad Right Stick Right",
    display: [RightJoystickIcon, ArrowRightIcon],
    keycode: Keycode.GP_BUTTON_RS_RIGHT,
    webCodes: [],
    category: "Gamepad",
  },
  {
    name: "Gamepad Left Trigger",
    tooltip: "Gamepad Left Trigger",
    display: [Gamepad2Icon, "LT"],
    keycode: Keycode.GP_BUTTON_LT,
    webCodes: [],
    category: "Gamepad",
  },
  {
    name: "Gamepad Right Trigger",
    tooltip: "Gamepad Right Trigger",
    display: [Gamepad2Icon, "RT"],
    keycode: Keycode.GP_BUTTON_RT,
    webCodes: [],
    category: "Gamepad",
  },
]

export const gamepadKeycodes = [
  Keycode.GP_BUTTON_A,
  Keycode.GP_BUTTON_B,
  Keycode.GP_BUTTON_X,
  Keycode.GP_BUTTON_Y,
  Keycode.GP_BUTTON_START,
  Keycode.GP_BUTTON_BACK,
  Keycode.GP_BUTTON_HOME,
  Keycode.GP_BUTTON_UP,
  Keycode.GP_BUTTON_DOWN,
  Keycode.GP_BUTTON_LEFT,
  Keycode.GP_BUTTON_RIGHT,
  Keycode.GP_BUTTON_LS_UP,
  Keycode.GP_BUTTON_LS_DOWN,
  Keycode.GP_BUTTON_LS_LEFT,
  Keycode.GP_BUTTON_LS_RIGHT,
  Keycode.GP_BUTTON_LS,
  Keycode.GP_BUTTON_RS_UP,
  Keycode.GP_BUTTON_RS_DOWN,
  Keycode.GP_BUTTON_RS_LEFT,
  Keycode.GP_BUTTON_RS_RIGHT,
  Keycode.GP_BUTTON_RS,
  Keycode.GP_BUTTON_LB,
  Keycode.GP_BUTTON_LT,
  Keycode.GP_BUTTON_RB,
  Keycode.GP_BUTTON_RT,
]

export function gamepadButtonToKeycode(button: number) {
  return button - HMK_GamepadButton.A + Keycode.GP_BUTTON_A
}

export function gamepadKeycodeToButton(keycode: number) {
  return keycode - Keycode.GP_BUTTON_A + HMK_GamepadButton.A
}
