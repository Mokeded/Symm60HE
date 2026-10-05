/// <reference lib="webworker" />

import { build, files, version } from "$service-worker"

const worker = self as unknown as ServiceWorkerGlobalScope
const cacheName = `symm60he-configurator-${version}`
const appAssets = [...build, ...files]

worker.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(cacheName)
      .then((cache) => cache.addAll(appAssets))
      .then(() => worker.skipWaiting()),
  )
})

worker.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter(
              (key) =>
                key.startsWith("symm60he-configurator-") && key !== cacheName,
            )
            .map((key) => caches.delete(key)),
        ),
      )
      .then(() => worker.clients.claim()),
  )
})

worker.addEventListener("fetch", (event) => {
  const { request } = event
  const url = new URL(request.url)
  if (request.method !== "GET" || url.origin !== worker.location.origin) return

  event.respondWith(
    caches.match(request).then(async (cached) => {
      if (cached) return cached
      const response = await fetch(request)
      if (response.ok) {
        const cache = await caches.open(cacheName)
        await cache.put(request, response.clone())
      }
      return response
    }),
  )
})
