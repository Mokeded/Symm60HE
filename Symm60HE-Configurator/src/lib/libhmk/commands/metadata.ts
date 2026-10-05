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

import { DataViewReader } from "$lib/data-view-reader"
import { uint32ToUInt8s } from "$lib/integer"
import type { Commander } from "$lib/keyboard/commander"
import { keyboardMetadataSchema } from "$lib/keyboard/metadata"
import z from "zod"
import { HMK_Command } from "."

const GET_METADATA_MAX_ENTRIES = 59

export async function getMetadata(commander: Commander) {
  const compressedMetadata: number[] = []
  while (true) {
    const reader = new DataViewReader(
      await commander.sendCommand({
        command: HMK_Command.GET_METADATA,
        payload: [...uint32ToUInt8s(compressedMetadata.length)],
      }),
    )

    const len = reader.uint32()
    compressedMetadata.push(
      ...[...Array(Math.min(len, GET_METADATA_MAX_ENTRIES))].map(() =>
        reader.uint8(),
      ),
    )

    if (len <= GET_METADATA_MAX_ENTRIES) {
      break
    }
  }

  const stream = new ReadableStream({
    pull(controller) {
      controller.enqueue(new Uint8Array(compressedMetadata))
      controller.close()
    },
  })
  const ds = new DecompressionStream("gzip")
  const decompressed = stream.pipeThrough(ds)
  const metadataStr = await new Response(decompressed).text()

  try {
    return keyboardMetadataSchema.parse(JSON.parse(metadataStr))
  } catch (err) {
    if (err instanceof SyntaxError) {
      throw new Error("The keyboard metadata is not a valid JSON.")
    } else if (err instanceof z.ZodError) {
      console.error(z.treeifyError(err))
      throw new Error("The keyboard metadata is not a valid metadata.")
    }
    throw err
  }
}
