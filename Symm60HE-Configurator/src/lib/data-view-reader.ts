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

export class DataViewReader {
  view: DataView
  offset: number

  constructor(view: DataView, offset = 0) {
    this.view = view
    this.offset = offset
  }

  uint8() {
    const ret = this.view.getUint8(this.offset)
    this.offset += 1

    return ret
  }

  uint16() {
    const ret = this.view.getUint16(this.offset, true)
    this.offset += 2

    return ret
  }

  uint32() {
    const ret = this.view.getUint32(this.offset, true)
    this.offset += 4

    return ret
  }
}
