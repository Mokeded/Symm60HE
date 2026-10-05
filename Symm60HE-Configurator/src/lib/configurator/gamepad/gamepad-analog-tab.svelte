<script lang="ts">
  import FixedScrollArea from "$lib/components/fixed-scroll-area.svelte"
  import Switch from "$lib/components/switch.svelte"
  import { cn, type WithoutChildren } from "$lib/utils"
  import type { HTMLAttributes } from "svelte/elements"
  import { gamepadQueryContext } from "../queries/gamepad-query.svelte"
  import AnalogCurve from "./analog-curve/analog-curve.svelte"

  const {
    class: className,
    ...props
  }: WithoutChildren<HTMLAttributes<HTMLDivElement>> = $props()

  const gamepadQuery = gamepadQueryContext.get()
  const { current: options } = $derived(gamepadQuery.gamepadOptions)
</script>

<div class={cn("grid grid-cols-[minmax(0,1fr)_28rem]", className)} {...props}>
  <FixedScrollArea class="flex flex-col gap-4 p-6 pt-2 pr-4">
    <div class="grid text-sm">
      <span class="font-medium">Configure Analog Curve</span>
      <span class="text-muted-foreground">
        Modify how keyboard analog values translate to gamepad analog inputs.
        You can manually adjust the analog curve or select a preset from below.
        These settings affect both joysticks and triggers.
      </span>
    </div>
    <AnalogCurve />
  </FixedScrollArea>
  <FixedScrollArea class="flex flex-col gap-4 p-6 pt-2 pl-4">
    <Switch
      bind:checked={
        () => options?.squareJoystick ?? false,
        (v) =>
          options &&
          gamepadQuery.setOptions({
            data: { ...options, squareJoystick: v },
          })
      }
      description="Remove the circular boundaries of the joystick for full range of motion."
      disabled={!options}
      id="square-joystick"
      title="Square Joystick Mode"
    />
    <Switch
      bind:checked={
        () => options?.snappyJoystick ?? false,
        (v) =>
          options &&
          gamepadQuery.setOptions({
            data: { ...options, snappyJoystick: v },
          })
      }
      description="Use the maximum analog value between opposite joystick axes instead of combining them for more responsive movement."
      disabled={!options}
      id="snappy-joystick"
      title="Snappy Joystick"
    />
  </FixedScrollArea>
</div>
