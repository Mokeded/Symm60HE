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

import { HMK_Command, HMK_RAW_HID_EP_SIZE } from "$lib/libhmk/commands"
import { TaskQueue } from "$lib/task-queue"

export class Commander {
  hidDevice: HIDDevice
  #taskQueue = new TaskQueue()
  #responseQueue: DataView[] = []

  constructor(hidDevice: HIDDevice) {
    this.hidDevice = hidDevice
    this.hidDevice.oninputreport = (e) => {
      if (e.data.byteLength === HMK_RAW_HID_EP_SIZE) {
        this.#responseQueue.push(e.data)
      } else {
        console.error(
          `Unexpected input report length: ${e.data.byteLength} bytes. Expected ${HMK_RAW_HID_EP_SIZE} bytes.`,
        )
      }
    }
  }

  async clear() {
    this.hidDevice.oninputreport = null
    await this.#taskQueue.clear()
    this.#responseQueue.length = 0
  }

  sendCommand(options: {
    command: HMK_Command
    payload?: number[]
    timeout?: number
  }) {
    const { command, payload = [], timeout = 4000 } = options

    if (payload.length > HMK_RAW_HID_EP_SIZE - 1) {
      throw new Error(
        `Payload size exceeds maximum limit of ${HMK_RAW_HID_EP_SIZE - 1} bytes.`,
      )
    }

    const commandBuffer = [
      command,
      ...payload,
      ...Array(HMK_RAW_HID_EP_SIZE - payload.length - 1).fill(0),
    ]

    return this.#taskQueue.enqueue(
      (abortController) =>
        new Promise<DataView>((resolve, reject) => {
          this.hidDevice
            .sendReport(0, new Uint8Array(commandBuffer))
            .catch((err) => reject(err))

          const interval = setInterval(() => {
            while (this.#responseQueue.length > 0) {
              const response = this.#responseQueue.shift()
              if (response !== undefined && response?.getUint8(0) === command) {
                clearInterval(interval)
                resolve(new DataView(response.buffer.slice(1)))
              }
            }
          }, 10)

          abortController.signal.addEventListener("abort", () => {
            clearInterval(interval)
            reject(new Error("Command was cancelled."))
          })

          setTimeout(() => {
            clearInterval(interval)
            reject(new Error("Command timed out."))
          }, timeout)
        }),
    )
  }
}
