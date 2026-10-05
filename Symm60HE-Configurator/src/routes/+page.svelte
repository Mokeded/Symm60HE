<!--
This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
details.

You should have received a copy of the GNU General Public License along with
this program. If not, see <https://www.gnu.org/licenses/>.
-->

<script lang="ts">
  import { CableIcon } from "@lucide/svelte"
  import Footer from "$lib/components/footer.svelte"
  import { Badge } from "$lib/components/ui/badge"
  import { Button } from "$lib/components/ui/button"
  import Configurator from "$lib/configurator/configurator.svelte"
  import type { Keyboard } from "$lib/keyboard"
  import { connect } from "$lib/keyboard/hmk-keyboard.svelte"
  import { HMK_FIRMWARE_MAX_VERSION } from "$lib/libhmk"
  import { toast } from "svelte-sonner"

  let keyboard: Keyboard | null = $state(null)

  const handleConnect = async () => {
    try {
      keyboard = await connect(({ metadata: { name } }) => {
        toast.success(`${name} disconnected.`)
        keyboard = null
      })
      if (keyboard) {
        let message = `Successfully connected to ${keyboard.metadata.name}.`
        if (keyboard.version < HMK_FIRMWARE_MAX_VERSION) {
          message += " Newer version of the firmware is available."
        }
        toast.success(message)
      }
    } catch (err) {
      toast.error(String(err))
    }
  }
</script>

{#if keyboard}
  <Configurator {keyboard} />
{:else}
  <main class="relative isolate flex-1 overflow-hidden py-20 sm:py-28">
    <div
      class="absolute inset-x-0 top-0 -z-10 h-80 bg-[radial-gradient(ellipse_at_top,rgba(91,74,232,0.20),transparent_70%)]"
    ></div>
    <div class="mx-auto max-w-6xl px-6">
      <div class="mx-auto max-w-3xl text-center">
        <Badge variant="secondary">Firmware v1.9 · WebHID</Badge>
        <h1 class="mt-5 text-5xl font-semibold tracking-tight sm:text-6xl">
          Symm60HE Configurator
        </h1>
        <p class="mt-5 text-lg font-medium text-wrap text-muted-foreground">
          The dedicated control surface for the Mokeded Symm60HE. Configure the
          keyboard directly from Chrome or Edge—no downloaded application or
          account is required.
        </p>
        <div class="mt-8 flex items-center justify-center">
          <Button onclick={() => handleConnect()} size="lg">
            <CableIcon /> Connect Symm60HE
          </Button>
        </div>
        <p class="mt-3 text-sm text-muted-foreground">
          Requires a Chromium browser and an HTTPS or localhost connection.
        </p>
      </div>

      <div class="mt-16 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <div class="rounded-xl border bg-card p-5 shadow-sm">
          <h2 class="font-semibold">Split RGB lighting</h2>
          <p class="mt-2 text-sm text-muted-foreground">
            Control both LED chains with solid, breathing, rainbow, and wave
            effects, plus color, brightness, speed, and mirrored animation.
          </p>
        </div>
        <div class="rounded-xl border bg-card p-5 shadow-sm">
          <h2 class="font-semibold">Performance</h2>
          <p class="mt-2 text-sm text-muted-foreground">
            Set per-key actuation, rapid-trigger press and release distances,
            continuous rapid trigger, and 1 kHz or 8 kHz polling.
          </p>
        </div>
        <div class="rounded-xl border bg-card p-5 shadow-sm">
          <h2 class="font-semibold">Four physical layouts</h2>
          <p class="mt-2 text-sm text-muted-foreground">
            Switch between WKL or arrow corners and split or 2U Backspace while
            inactive Hall channels remain masked by firmware.
          </p>
        </div>
        <div class="rounded-xl border bg-card p-5 shadow-sm">
          <h2 class="font-semibold">Remapping and layers</h2>
          <p class="mt-2 text-sm text-muted-foreground">
            Edit the four keymap layers in every profile and import, export,
            duplicate, or restore profile configurations.
          </p>
        </div>
        <div class="rounded-xl border bg-card p-5 shadow-sm">
          <h2 class="font-semibold">Advanced keys</h2>
          <p class="mt-2 text-sm text-muted-foreground">
            Configure SOCD/null binds, dynamic keystrokes, tap-hold actions,
            toggles, macros, and advanced-key tick rates.
          </p>
        </div>
        <div class="rounded-xl border bg-card p-5 shadow-sm">
          <h2 class="font-semibold">Analog gamepad</h2>
          <p class="mt-2 text-sm text-muted-foreground">
            Assign XInput buttons and sticks, then tune analog curves, square
            joystick, snappy joystick, and keyboard/gamepad behavior.
          </p>
        </div>
        <div class="rounded-xl border bg-card p-5 shadow-sm lg:col-span-2">
          <h2 class="font-semibold">Calibration and recovery</h2>
          <p class="mt-2 text-sm text-muted-foreground">
            Watch all 69 Hall channels live, recalibrate, tune thresholds,
            restart, enter the bootloader, or restore firmware defaults.
          </p>
        </div>
      </div>
    </div>
  </main>
  <Footer />
{/if}
