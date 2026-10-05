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

import { displayUInt16 } from "$lib/integer"
import type { KeyboardMetadata } from "$lib/keyboard/metadata"
import { Keycode, MO_GET_LAYER, PF_GET_PROFILE } from "$lib/libhmk/keycodes"
import type { Component } from "svelte"
import { advancedKeysKeycodeMetadata } from "./advanced-keys"
import { basicKeycodeMetadata, basicKeycodes } from "./basic"
import { extendedKeycodeMetadata, extendedKeycodes } from "./extended"
import { gamepadKeycodeMetadata } from "./gamepad"
import { mediaKeycodeMetadata, mediaKeycodes } from "./media"
import { mouseKeycodeMetadata, mouseKeycodes } from "./mouse"
import { getProfilesKeycodes, profilesKeycodeMetadata } from "./profiles"
import { getSpecialKeycodes, specialKeycodeMetadata } from "./special"

export const keycodeCategories = {
  BASIC: "Basic",
  EXTENDED: "Extended",
  SPECIAL: "Special",
  PROFILES: "Profiles",
  MEDIA: "Media",
  MOUSE: "Mouse",
  ADVANCED_KEYS: "Advanced Keys",
  GAMEPAD: "Gamepad",
  UNKNOWN: "Unknown",
} as const

export type KeycodeCategory =
  (typeof keycodeCategories)[keyof typeof keycodeCategories]

export type KeycodeMetadata = {
  name: string
  tooltip?: string
  display?: (string | Component)[]
  keycode: Keycode
  webCodes: string[]
  category: KeycodeCategory
}

export const keycodeMetadata: KeycodeMetadata[] = [
  ...basicKeycodeMetadata,
  ...extendedKeycodeMetadata,
  ...specialKeycodeMetadata,
  ...profilesKeycodeMetadata,
  ...mediaKeycodeMetadata,
  ...mouseKeycodeMetadata,
  ...advancedKeysKeycodeMetadata,
  ...gamepadKeycodeMetadata,
]

const keycodeMetadataMap = new Map(
  keycodeMetadata.map((metadata) => [metadata.keycode, metadata]),
)

export function getKeycodeMetadata(keycode: Keycode): KeycodeMetadata {
  if (Keycode.SP_MO_MIN <= keycode && keycode <= Keycode.SP_MO_MAX) {
    const layer = MO_GET_LAYER(keycode)
    return {
      name: `MO(${layer})`,
      tooltip: `Hold to Activate Layer ${layer}`,
      keycode,
      webCodes: [],
      category: "Special",
    }
  }

  if (Keycode.SP_PF_MIN <= keycode && keycode <= Keycode.SP_PF_MAX) {
    const profile = PF_GET_PROFILE(keycode)
    return {
      name: `PF(${profile})`,
      tooltip: `Switch to Profile ${profile}`,
      keycode,
      webCodes: [],
      category: "Profiles",
    }
  }

  return (
    keycodeMetadataMap.get(keycode) ?? {
      name: displayUInt16(keycode),
      tooltip: `Unknown Keycode: ${displayUInt16(keycode)}`,
      keycode,
      webCodes: [],
      category: "Unknown",
    }
  )
}

export function getCategorizedKeycodes({
  numProfiles,
  numLayers,
}: KeyboardMetadata): [KeycodeCategory, number[]][] {
  return [
    ["Basic", basicKeycodes],
    ["Extended", extendedKeycodes],
    ["Special", getSpecialKeycodes(numLayers)],
    ["Profiles", getProfilesKeycodes(numProfiles)],
    ["Media", mediaKeycodes],
    ["Mouse", mouseKeycodes],
  ]
}
