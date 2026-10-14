export type {
  AvailabilityStatus,
  Booking,
  BookingStatus,
  LocationItem,
  MarketplacePage,
  PublicRescuer,
  RescuerVerificationStatus,
} from "@spilton/shared-types";

export type DirectoryLocation = {
  state_code: string;
  district_code: string;
  subdistrict_code: string;
  village_code: string;
};

export type MarketplaceLocation = DirectoryLocation & {
  latitude?: number;
  longitude?: number;
  accuracy?: number;
  manualAddress: string;
  landmark: string;
};
