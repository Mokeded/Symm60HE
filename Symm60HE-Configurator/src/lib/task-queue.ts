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

type TaskQueueTask = {
  task: (abortController: AbortController) => Promise<void>
  cancel: () => void
}

export class TaskQueue {
  #tasks: TaskQueueTask[] = []
  #isRunning = false
  #waitForCurrentTask: Promise<void> | null = null
  #abortController = new AbortController()

  async enqueue<T>(task: (abortController: AbortController) => Promise<T>) {
    return new Promise<T>((resolve, reject) => {
      this.#tasks.push({
        task: async (abortController) => {
          try {
            resolve(await task(abortController))
          } catch (err) {
            reject(err)
          }
        },
        cancel: () => reject(new Error("Task was cancelled")),
      })
      if (!this.#isRunning) {
        this.#isRunning = true
        this.#tick()
      }
    })
  }

  async clear() {
    const tasks = this.#tasks

    this.#tasks = []
    for (const task of tasks) {
      task.cancel()
    }

    this.#abortController.abort()
    this.#abortController = new AbortController()
    if (this.#waitForCurrentTask !== null) {
      await this.#waitForCurrentTask
    }
  }

  async #tick() {
    const task = this.#tasks.shift()
    if (task) {
      this.#waitForCurrentTask = task.task(this.#abortController).then(() => {
        this.#waitForCurrentTask = null
        this.#tick()
      })
    } else {
      this.#isRunning = false
    }
  }
}
