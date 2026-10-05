<!--
This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.
-->

<script lang="ts">
  import { GaugeIcon, LightbulbIcon, WavesIcon, ZapIcon } from "@lucide/svelte"
  import CommitSlider from "$lib/components/commit-slider.svelte"
  import FixedScrollArea from "$lib/components/fixed-scroll-area.svelte"
  import Switch from "$lib/components/switch.svelte"
  import { Button } from "$lib/components/ui/button"
  import * as Select from "$lib/components/ui/select"
  import { keyboardContext } from "$lib/keyboard"
  import {
    HMK_RGB_EFFECT_NAMES,
    HMK_RGBEffect,
    type HMK_RGBConfig,
  } from "$lib/libhmk/rgb"
  import { cn, type WithoutChildren } from "$lib/utils"
  import { onMount } from "svelte"
  import type { HTMLAttributes } from "svelte/elements"
  import { rgbQueryContext } from "../queries/rgb-query.svelte"

  const {
    class: className,
    ...props
  }: WithoutChildren<HTMLAttributes<HTMLDivElement>> = $props()

  const metadata = keyboardContext.get().metadata.rgb
  const rgbQuery = rgbQueryContext.get()
  const { current: config } = $derived(rgbQuery.config)
  let animationTime = $state(0)

  const effects = Object.entries(HMK_RGB_EFFECT_NAMES).map(
    ([value, label]) => ({
      value: Number(value) as HMK_RGBEffect,
      label,
    }),
  )

  const presets = [
    { name: "Violet", value: "#5b4ae8" },
    { name: "Ice", value: "#43c6ff" },
    { name: "Mint", value: "#37e59d" },
    { name: "Amber", value: "#ffb020" },
    { name: "Rose", value: "#ff477e" },
    { name: "White", value: "#ffffff" },
  ]

  onMount(() => {
    let frame = 0
    const tick = (time: number) => {
      animationTime = time
      frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  })

  function update(patch: Partial<HMK_RGBConfig>) {
    const current = rgbQuery.config.current
    if (!current) return
    void rgbQuery.set({ data: { ...current, ...patch } })
  }

  function colorHex({ red, green, blue }: HMK_RGBConfig) {
    return `#${[red, green, blue]
      .map((channel) => channel.toString(16).padStart(2, "0"))
      .join("")}`
  }

  function colorPatch(value: string) {
    return {
      red: Number.parseInt(value.slice(1, 3), 16),
      green: Number.parseInt(value.slice(3, 5), 16),
      blue: Number.parseInt(value.slice(5, 7), 16),
    }
  }

  function wheel(position: number): [number, number, number] {
    let p = ((Math.round(position) % 256) + 256) % 256
    if (p < 85) return [255 - p * 3, p * 3, 0]
    if (p < 170) {
      p -= 85
      return [0, 255 - p * 3, p * 3]
    }
    p -= 170
    return [p * 3, 0, 255 - p * 3]
  }

  function triangleWave(position: number) {
    const p = ((Math.round(position) % 256) + 256) % 256
    return p < 128 ? p * 2 : (255 - p) * 2
  }

  const preview = $derived.by(() => {
    if (!config || !metadata)
      return { outputs: [] as string[][], estimatedMa: 0 }

    const phase = ((animationTime / 8) * (config.speed + 16)) / 128
    let frameBrightness = config.brightness
    if (config.effect === HMK_RGBEffect.BREATHING) {
      frameBrightness *= (32 + (triangleWave(phase) * 7) / 8) / 255
    }

    const raw = metadata.outputs.map((output, outputIndex) =>
      Array.from({ length: output.ledCount }, (_, ledIndex) => {
        const effectLED =
          config.splitMirror && outputIndex % 2 === 1
            ? output.ledCount - 1 - ledIndex
            : ledIndex
        let color: [number, number, number] = [
          config.red,
          config.green,
          config.blue,
        ]
        let brightness = frameBrightness
        if (config.effect === HMK_RGBEffect.RAINBOW) {
          color = wheel(phase + effectLED * 7)
        } else if (config.effect === HMK_RGBEffect.WAVE) {
          brightness *=
            (24 + (triangleWave(phase + effectLED * 12) * 231) / 255) / 255
        }
        if (!config.enabled) brightness = 0
        return color.map((channel) => (channel * brightness) / 255) as [
          number,
          number,
          number,
        ]
      }),
    )

    const channelSum = raw.flat(2).reduce((sum, channel) => sum + channel, 0)
    const estimatedMa = (channelSum * 12) / 255
    const limiter =
      estimatedMa > metadata.currentLimitMa
        ? metadata.currentLimitMa / estimatedMa
        : 1

    return {
      outputs: raw.map((output) =>
        output.map(
          ([red, green, blue]) =>
            `rgb(${Math.round(red * limiter)}, ${Math.round(green * limiter)}, ${Math.round(blue * limiter)})`,
        ),
      ),
      estimatedMa: Math.min(estimatedMa, metadata.currentLimitMa),
    }
  })
</script>

<div class={cn("mx-auto size-full max-w-5xl", className)} {...props}>
  <FixedScrollArea class="flex flex-col gap-5 p-5">
    {#if !metadata}
      <div class="rounded-xl border bg-card p-6 text-sm text-muted-foreground">
        This firmware does not report any RGB outputs.
      </div>
    {:else if !config}
      <div class="rounded-xl border bg-card p-6 text-sm text-muted-foreground">
        Reading the lighting configuration from the keyboard…
      </div>
    {:else}
      <section class="overflow-hidden rounded-2xl border bg-card shadow-sm">
        <div class="flex items-start justify-between gap-5 border-b p-5">
          <div class="flex gap-3">
            <div class="rounded-xl bg-primary/10 p-2.5 text-primary">
              <LightbulbIcon class="size-5" />
            </div>
            <div>
              <h2 class="font-semibold">Split RGB preview</h2>
              <p class="mt-1 max-w-2xl text-sm text-muted-foreground">
                A live representation of both addressable LED chains. Changes
                are written to the keyboard and retained across restarts.
              </p>
            </div>
          </div>
          <div
            class="rounded-full border px-3 py-1 text-xs font-medium {config.enabled
              ? 'bg-primary/10 text-primary'
              : 'text-muted-foreground'}"
          >
            {config.enabled ? "Lighting on" : "Lighting off"}
          </div>
        </div>

        <div class="grid gap-4 bg-muted/30 p-5 md:grid-cols-2">
          {#each metadata.outputs as output, outputIndex (output.name)}
            <div class="rounded-xl border bg-background/80 p-4">
              <div class="mb-3 flex items-center justify-between gap-3">
                <span class="text-sm font-medium">{output.name}</span>
                <span class="text-xs text-muted-foreground">
                  {output.ledCount} LEDs
                </span>
              </div>
              <div
                class="grid gap-1.5"
                style="grid-template-columns: repeat(10, minmax(0, 1fr));"
                aria-label={`${output.name} RGB preview`}
              >
                {#each preview.outputs[outputIndex] ?? [] as color, ledIndex (ledIndex)}
                  <div
                    class="aspect-square rounded-[0.3rem] border border-black/10 transition-colors duration-75 dark:border-white/10"
                    style={`background-color: ${color}; box-shadow: 0 0 10px color-mix(in srgb, ${color} 55%, transparent);`}
                    title={`${output.name} LED ${ledIndex + 1}`}
                  ></div>
                {/each}
              </div>
            </div>
          {/each}
        </div>

        <div
          class="grid gap-3 border-t px-5 py-3 text-xs text-muted-foreground sm:grid-cols-3"
        >
          <span class="flex items-center gap-2">
            <ZapIcon class="size-3.5 text-primary" />
            {metadata.currentLimitMa} mA firmware limit
          </span>
          <span class="flex items-center gap-2">
            <GaugeIcon class="size-3.5 text-primary" />
            ~{Math.round(preview.estimatedMa)} mA preview load
          </span>
          <span class="flex items-center gap-2">
            <WavesIcon class="size-3.5 text-primary" />
            {metadata.refreshHz} Hz animation refresh
          </span>
        </div>
      </section>

      <div class="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(18rem,0.72fr)]">
        <section class="rounded-2xl border bg-card p-5 shadow-sm">
          <h2 class="font-semibold">Effect</h2>
          <div class="mt-5 flex flex-col gap-5">
            <Switch
              bind:checked={
                () => config.enabled, (enabled) => update({ enabled })
              }
              id="rgb-enabled"
              title="RGB lighting"
              description="Enable or disable both lighting chains without changing the saved effect or color."
            />

            <div class="grid gap-1.5 text-sm">
              <label class="font-medium" for="rgb-effect">Animation</label>
              <Select.Root
                bind:value={
                  () => String(config.effect),
                  (value) => update({ effect: Number(value) as HMK_RGBEffect })
                }
                type="single"
              >
                <Select.Trigger
                  class="w-full"
                  disabled={!config.enabled}
                  id="rgb-effect"
                >
                  {HMK_RGB_EFFECT_NAMES[config.effect]}
                </Select.Trigger>
                <Select.Content class="w-[var(--bits-select-anchor-width)]">
                  {#each effects as effect (effect.value)}
                    <Select.Item value={String(effect.value)}>
                      {effect.label}
                    </Select.Item>
                  {/each}
                </Select.Content>
              </Select.Root>
              <span class="text-muted-foreground">
                Solid is static; breathing, rainbow, and wave animate on-device.
              </span>
            </div>

            <CommitSlider
              committed={config.brightness}
              disabled={!config.enabled}
              display={(value) => `${Math.round((value / 255) * 100)}%`}
              max={255}
              min={0}
              onCommit={(brightness) => update({ brightness })}
              title="Brightness"
              description="The firmware reduces output further when necessary to stay inside its current budget."
            />

            <CommitSlider
              committed={config.speed}
              disabled={!config.enabled ||
                config.effect === HMK_RGBEffect.SOLID}
              display={(value) => `${Math.round((value / 255) * 100)}%`}
              max={255}
              min={0}
              onCommit={(speed) => update({ speed })}
              title="Animation speed"
            />

            <Switch
              bind:checked={
                () => config.splitMirror,
                (splitMirror) => update({ splitMirror })
              }
              disabled={!config.enabled}
              id="rgb-split-mirror"
              title="Mirror the right half"
              description="Reverse the animation direction on the right chain so both halves move symmetrically from the center."
            />
          </div>
        </section>

        <section class="rounded-2xl border bg-card p-5 shadow-sm">
          <h2 class="font-semibold">Base color</h2>
          <p class="mt-1 text-sm text-muted-foreground">
            Used by solid, breathing, and wave. Rainbow generates its own
            colors.
          </p>

          <div class="mt-5 flex items-center gap-4">
            <label
              class="relative block size-20 shrink-0 overflow-hidden rounded-2xl border shadow-sm"
              style={`background: ${colorHex(config)}`}
            >
              <input
                aria-label="Choose RGB color"
                class="absolute inset-0 size-full cursor-pointer opacity-0"
                disabled={!config.enabled ||
                  config.effect === HMK_RGBEffect.RAINBOW}
                onchange={(event) =>
                  update(colorPatch(event.currentTarget.value))}
                type="color"
                value={colorHex(config)}
              />
            </label>
            <div>
              <div class="font-mono text-sm font-semibold uppercase">
                {colorHex(config)}
              </div>
              <div class="mt-1 text-xs text-muted-foreground">
                RGB {config.red}, {config.green}, {config.blue}
              </div>
            </div>
          </div>

          <div class="mt-5 grid grid-cols-3 gap-2">
            {#each presets as preset (preset.name)}
              <Button
                aria-label={`Use ${preset.name}`}
                class="justify-start px-2"
                disabled={!config.enabled ||
                  config.effect === HMK_RGBEffect.RAINBOW}
                onclick={() => update(colorPatch(preset.value))}
                size="sm"
                variant="outline"
              >
                <span
                  class="size-3.5 rounded-full border border-black/10"
                  style={`background: ${preset.value}`}
                ></span>
                {preset.name}
              </Button>
            {/each}
          </div>

          <div
            class="mt-5 rounded-xl bg-muted/50 p-3 text-xs leading-relaxed text-muted-foreground"
          >
            The {metadata.currentLimitMa} mA ceiling is applied after brightness and
            effects, reserving part of the keyboard’s declared USB power budget for
            the MCU and sensors. Actual assembled-board current should still be confirmed
            during hardware validation.
          </div>
        </section>
      </div>
    {/if}
  </FixedScrollArea>
</div>
