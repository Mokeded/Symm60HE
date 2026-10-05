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

import z from "zod"

export const uint8Schema = z.int().min(0x00).max(0xff)
export const uint16Schema = z.int().min(0x00).max(0xffff)
export const uint32Schema = z.int().min(0x00).max(0xffffffff)

export function displayUInt8(v: number) {
  return `0x${v.toString(16).padStart(2, "0")}`
}

export function displayUInt16(v: number) {
  return `0x${v.toString(16).padStart(4, "0")}`
}

export function displayUInt32(v: number) {
  return `0x${v.toString(16).padStart(8, "0")}`
}

export function uint16ToUInt8s(v: number) {
  return [v & 0xff, (v >> 8) & 0xff]
}

export function uint32ToUInt8s(v: number) {
  return [v & 0xff, (v >> 8) & 0xff, (v >> 16) & 0xff, (v >> 24) & 0xff]
}
