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

export const EM_PER_UNIT = 4

export function unitToEM(v: number) {
  return v * EM_PER_UNIT
}

export function unitToEMString(v: number) {
  return `${unitToEM(v)}em`
}

export function unitToStyle(w = 1, h = 1, x = 0, y = 0) {
  let ret = `width: ${unitToEMString(w)}; height: ${unitToEMString(h)};`
  if (x > 0) ret += ` left: ${unitToEMString(x)};`
  if (y > 0) ret += ` top: ${unitToEMString(y)};`
  return ret
}
