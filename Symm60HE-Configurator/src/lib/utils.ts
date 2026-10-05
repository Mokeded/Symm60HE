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

import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"
import { featureVersionMap, type Feature } from "./libhmk"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function isWebHIDSSupported() {
  return !!navigator.hid
}

export function displayVersion(v: number) {
  return `v${v >> 8}.${v & 0xff}`
}

export function stringNullable<T>(v: T | null) {
  return v === null ? "" : String(v)
}

export function numberNullable(v: string) {
  return v === "" ? null : Number(v)
}

export function optMap<T, U>(v: T | null | undefined, f: (v: T) => U) {
  return v === null || v === undefined ? undefined : f(v)
}

export function clamp(v: number, bound: [number, number]) {
  return Math.min(Math.max(v, bound[0]), bound[1])
}

export function setToIntervals(set: Set<number>) {
  const arr = [...set].toSorted()
  const ret: [number, number][] = []

  for (const x of arr) {
    const back = ret[ret.length - 1]
    if (back && back[0] + back[1] === x) back[1]++
    else ret.push([x, 1])
  }

  return ret
}

export function isFeatureAvailable(feature: Feature, version: number) {
  return featureVersionMap[feature] <= version
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type WithoutChild<T> = T extends { child?: any } ? Omit<T, "child"> : T
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type WithoutChildren<T> = T extends { children?: any }
  ? Omit<T, "children">
  : T
export type WithoutChildrenOrChild<T> = WithoutChildren<WithoutChild<T>>
export type WithElementRef<T, U extends HTMLElement = HTMLElement> = T & {
  ref?: U | null
}
