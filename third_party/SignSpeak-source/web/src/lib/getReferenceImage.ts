import { REFERENCE_IMAGE_VERSIONS } from "@/generated/referenceImageVersions";
import logoPath from "@/assets/logo.png";

const VALID_LETTERS = /^[A-Z]$/;

export function getLogoPath(): string {
  return logoPath;
}

export function getReferenceImage(letter: string): string {
  const normalized = String(letter || "").trim().toUpperCase();
  if (!VALID_LETTERS.test(normalized)) {
    return getLogoPath();
  }

  const version = REFERENCE_IMAGE_VERSIONS[normalized];
  const path = `${import.meta.env.BASE_URL}assets/reference/${normalized}_test.jpg`;

  return version ? `${path}?v=${version}` : path;
}
