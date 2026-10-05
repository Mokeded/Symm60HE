export const SYMM60HE_NAME = "Symm60HE"
export const SYMM60HE_VENDOR_ID = 0xab50
export const SYMM60HE_PRODUCT_ID = 0xab61
export const SYMM60HE_USAGE_PAGE = 0xffab
export const SYMM60HE_USAGE_ID = 0x00ab

export const SYMM60HE_HID_FILTER: HIDDeviceFilter = {
  vendorId: SYMM60HE_VENDOR_ID,
  productId: SYMM60HE_PRODUCT_ID,
  usagePage: SYMM60HE_USAGE_PAGE,
  usage: SYMM60HE_USAGE_ID,
}

export function isSymm60HEDevice(device: HIDDevice) {
  return (
    device.vendorId === SYMM60HE_VENDOR_ID &&
    device.productId === SYMM60HE_PRODUCT_ID &&
    device.collections.some(
      ({ usagePage, usage }) =>
        usagePage === SYMM60HE_USAGE_PAGE && usage === SYMM60HE_USAGE_ID,
    )
  )
}
