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
  AlarmClockIcon,
  ArrowBigLeftIcon,
  ArrowBigRightIcon,
  BookmarkIcon,
  CalculatorIcon,
  EarthIcon,
  FolderClosedIcon,
  Grid3x3Icon,
  LayoutDashboardIcon,
  MailIcon,
  MoonIcon,
  PowerIcon,
  RefreshCwIcon,
  SearchIcon,
  SunDimIcon,
  SunIcon,
} from "@lucide/svelte"
import { Keycode, MO } from "$lib/libhmk/keycodes"
import type { KeycodeMetadata } from "."

export const specialKeycodeMetadata: KeycodeMetadata[] = [
  {
    name: "System Power",
    tooltip: "System Power",
    display: [PowerIcon],
    keycode: Keycode.KC_SYSTEM_POWER,
    webCodes: ["Power"],
    category: "Special",
  },
  {
    name: "System Sleep",
    tooltip: "System Sleep",
    display: [MoonIcon],
    keycode: Keycode.KC_SYSTEM_SLEEP,
    webCodes: ["Sleep"],
    category: "Special",
  },
  {
    name: "System Wake",
    tooltip: "System Wake",
    display: [AlarmClockIcon],
    keycode: Keycode.KC_SYSTEM_WAKE,
    webCodes: ["WakeUp"],
    category: "Special",
  },

  {
    name: "Mail",
    tooltip: "Open Mail",
    display: [MailIcon],
    keycode: Keycode.KC_MAIL,
    webCodes: ["LaunchMail"],
    category: "Special",
  },
  {
    name: "Calculator",
    tooltip: "Open Calculator",
    display: [CalculatorIcon],
    keycode: Keycode.KC_CALCULATOR,
    webCodes: [],
    category: "Special",
  },
  {
    name: "File Browser",
    tooltip: "Open File Browser",
    display: [FolderClosedIcon],
    keycode: Keycode.KC_MY_COMPUTER,
    webCodes: [],
    category: "Special",
  },
  {
    name: "Browser Search",
    tooltip: "Browser Search",
    display: [SearchIcon],
    keycode: Keycode.KC_WWW_SEARCH,
    webCodes: ["BrowserSearch"],
    category: "Special",
  },
  {
    name: "Browser Home",
    tooltip: "Open Browser",
    display: [EarthIcon],
    keycode: Keycode.KC_WWW_HOME,
    webCodes: ["BrowserHome"],
    category: "Special",
  },
  {
    name: "Browser Back",
    tooltip: "Browser Back",
    display: [ArrowBigLeftIcon],
    keycode: Keycode.KC_WWW_BACK,
    webCodes: ["BrowserBack"],
    category: "Special",
  },
  {
    name: "Browser Forward",
    tooltip: "Browser Forward",
    display: [ArrowBigRightIcon],
    keycode: Keycode.KC_WWW_FORWARD,
    webCodes: ["BrowserForward"],
    category: "Special",
  },
  {
    name: "Browser Refresh",
    tooltip: "Browser Refresh",
    display: [RefreshCwIcon],
    keycode: Keycode.KC_WWW_REFRESH,
    webCodes: ["BrowserRefresh"],
    category: "Special",
  },
  {
    name: "Browser Favorites",
    tooltip: "Browser Favorites",
    display: [BookmarkIcon],
    keycode: Keycode.KC_WWW_FAVORITES,
    webCodes: ["BrowserFavorites"],
    category: "Special",
  },
  {
    name: "Brightness Up",
    tooltip: "Increase Screen Brightness",
    display: [SunIcon],
    keycode: Keycode.KC_BRIGHTNESS_UP,
    webCodes: [],
    category: "Special",
  },
  {
    name: "Brightness Down",
    tooltip: "Decrease Screen Brightness",
    display: [SunDimIcon],
    keycode: Keycode.KC_BRIGHTNESS_DOWN,
    webCodes: [],
    category: "Special",
  },
  {
    name: "Mission Control",
    tooltip: "Open macOS Mission Control",
    display: [LayoutDashboardIcon],
    keycode: Keycode.KC_MISSION_CONTROL,
    webCodes: [],
    category: "Special",
  },
  {
    name: "Launchpad",
    tooltip: "Open macOS Launchpad",
    display: [Grid3x3Icon],
    keycode: Keycode.KC_LAUNCHPAD,
    webCodes: [],
    category: "Special",
  },
  {
    name: "Key\nLock",
    tooltip: "Key Disable Toggle. Disable the same key in layer 0.",
    keycode: Keycode.SP_KEY_LOCK,
    webCodes: [],
    category: "Special",
  },
  {
    name: "Layer\nLock",
    tooltip:
      "Layer Toggle. Swap the default layer between layer 0 and the current layer.",
    keycode: Keycode.SP_LAYER_LOCK,
    webCodes: [],
    category: "Special",
  },
  {
    name: "Boot",
    tooltip: "Enter Bootloader Mode",
    keycode: Keycode.SP_BOOT,
    webCodes: [],
    category: "Special",
  },
]

export function getSpecialKeycodes(numLayers: number) {
  return [
    Keycode.KC_MAIL,
    Keycode.KC_CALCULATOR,
    Keycode.KC_MY_COMPUTER,
    Keycode.KC_WWW_SEARCH,
    Keycode.KC_WWW_HOME,
    Keycode.KC_WWW_BACK,
    Keycode.KC_WWW_FORWARD,
    Keycode.KC_WWW_REFRESH,
    Keycode.KC_WWW_FAVORITES,
    Keycode.KC_SYSTEM_POWER,
    Keycode.KC_SYSTEM_SLEEP,
    Keycode.KC_SYSTEM_WAKE,
    Keycode.KC_MISSION_CONTROL,
    Keycode.KC_LAUNCHPAD,
    Keycode.KC_BRIGHTNESS_DOWN,
    Keycode.KC_BRIGHTNESS_UP,
    Keycode.SP_KEY_LOCK,
    ...[...Array(numLayers)].map((_, i) => MO(i)),
    Keycode.SP_LAYER_LOCK,
    Keycode.SP_BOOT,
  ]
}
