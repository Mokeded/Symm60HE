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
  MusicIcon,
  PlayIcon,
  SkipBackIcon,
  SkipForwardIcon,
  SquareIcon,
  Volume1Icon,
  Volume2Icon,
  VolumeOffIcon,
} from "@lucide/svelte"
import { Keycode } from "$lib/libhmk/keycodes"
import type { KeycodeMetadata } from "."

export const mediaKeycodeMetadata: KeycodeMetadata[] = [
  {
    name: "Audio Mute",
    tooltip: "Mute Audio",
    display: [VolumeOffIcon],
    keycode: Keycode.KC_AUDIO_MUTE,
    webCodes: ["AudioVolumeMute", "VolumeMute"],
    category: "Media",
  },
  {
    name: "Audio Volume Up",
    tooltip: "Increase Audio Volume",
    display: [Volume2Icon],
    keycode: Keycode.KC_AUDIO_VOL_UP,
    webCodes: ["AudioVolumeUp", "VolumeUp"],
    category: "Media",
  },
  {
    name: "Audio Volume Down",
    tooltip: "Decrease Audio Volume",
    display: [Volume1Icon],
    keycode: Keycode.KC_AUDIO_VOL_DOWN,
    webCodes: ["AudioVolumeDown", "VolumeDown"],
    category: "Media",
  },
  {
    name: "Media Next Track",
    tooltip: "Media Next",
    display: [SkipForwardIcon],
    keycode: Keycode.KC_MEDIA_NEXT_TRACK,
    webCodes: ["MediaTrackNext"],
    category: "Media",
  },
  {
    name: "Media Previous Track",
    tooltip: "Media Previous",
    display: [SkipBackIcon],
    keycode: Keycode.KC_MEDIA_PREV_TRACK,
    webCodes: ["MediaTrackPrevious"],
    category: "Media",
  },
  {
    name: "Media Stop",
    tooltip: "Media Stop",
    display: [SquareIcon],
    keycode: Keycode.KC_MEDIA_STOP,
    webCodes: ["MediaStop"],
    category: "Media",
  },
  {
    name: "Media Play/Pause",
    tooltip: "Media Play/Pause",
    display: [PlayIcon],
    keycode: Keycode.KC_MEDIA_PLAY_PAUSE,
    webCodes: ["MediaPlayPause"],
    category: "Media",
  },
  {
    name: "Media Select",
    tooltip: "Open Media Player",
    display: [MusicIcon],
    keycode: Keycode.KC_MEDIA_SELECT,
    webCodes: ["MediaSelect"],
    category: "Media",
  },
]

export const mediaKeycodes = [
  Keycode.KC_MEDIA_SELECT,
  Keycode.KC_MEDIA_PREV_TRACK,
  Keycode.KC_MEDIA_PLAY_PAUSE,
  Keycode.KC_MEDIA_STOP,
  Keycode.KC_MEDIA_NEXT_TRACK,
  Keycode.KC_AUDIO_MUTE,
  Keycode.KC_AUDIO_VOL_DOWN,
  Keycode.KC_AUDIO_VOL_UP,
]
