/** Navigation uses meters and an explicit floor level; it never depends on rendering. */
export const SURVEY_FOOT_METERS = 1200 / 3937;

export function inside(point, polygon) {
  let hit = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const a = polygon[i],
      b = polygon[j];
    if (
      a[1] > point[1] !== b[1] > point[1] &&
      point[0] < ((b[0] - a[0]) * (point[1] - a[1])) / (b[1] - a[1]) + a[0]
    )
      hit = !hit;
  }
  return hit;
}

export const meters = (polygon) =>
  polygon.map((point) => point.map((n) => n * SURVEY_FOOT_METERS));

export class Navigation {
  constructor(data, obstacles) {
    this.floors = data.indoor.floors;
    this.parcel = meters(data.outdoor.parcel);
    this.zones = data.outdoor.zones.map((zone) => meters(zone.poly));
    this.surfaces = data.navigation?.surfaces || [];
    this.obstacles = obstacles;
  }

  ground(x, y, level = 0) {
    const floor = this.floors[level];
    if (level > 0 || inside([x, y], floor.outline)) return floor.base;
    const surface = this.surfaces.find((surface) =>
      inside([x, y], surface.polygon),
    );
    if (surface) return surface.height;
    const zone = this.zones.findIndex((polygon) => inside([x, y], polygon));
    return zone === 3 ? 0.8 : zone === 4 ? 0.4 : 0.016;
  }

  safe(x, y, level = 0) {
    const floor = this.floors[level],
      point = [x, y];
    if (!floor || !Number.isFinite(x) || !Number.isFinite(y)) return false;
    if (!inside(point, level > 0 ? floor.outline : this.parcel)) return false;
    if (
      level === 0 &&
      (inside(point, this.zones[0]) ||
        (inside(point, this.zones[5]) && (x < 3 || x > 4.03)))
    )
      return false;
    for (const wall of floor.walls) {
      const a = wall.a,
        b = wall.b,
        dx = b[0] - a[0],
        dy = b[1] - a[1];
      const length = Math.hypot(dx, dy);
      if (!length) continue;
      const t = Math.max(
        0,
        Math.min(1, ((x - a[0]) * dx + (y - a[1]) * dy) / (length * length)),
      );
      if (Math.hypot(x - a[0] - t * dx, y - a[1] - t * dy) > 0.27) continue;
      const doorway = wall.holes.some((hole) => {
        if (hole.window || (hole.sill ?? 0) >= 0.05) return false;
        const hx = hole.b[0] - hole.a[0],
          hy = hole.b[1] - hole.a[1],
          size = Math.hypot(hx, hy);
        if (!size) return false;
        const q = ((x - hole.a[0]) * hx + (y - hole.a[1]) * hy) / (size * size);
        return q > 0.22 / size && q < 1 - 0.22 / size;
      });
      if (!doorway) return false;
    }
    const z = this.ground(x, y, level);
    return !this.obstacles.some(
      (block) =>
        block.max[2] >= z + 0.1 &&
        block.min[2] <= z + 1.65 &&
        x > block.min[0] - 0.18 &&
        x < block.max[0] + 0.18 &&
        y > block.min[1] - 0.18 &&
        y < block.max[1] + 0.18,
    );
  }

  nearest(x, y, level = 0) {
    if (this.safe(x, y, level)) return [x, y];
    for (let radius = 0.2; radius <= 1.6; radius += 0.2) {
      for (let j = 0; j < 24; j++) {
        const angle = (j * Math.PI) / 12,
          px = x + radius * Math.cos(angle),
          py = y + radius * Math.sin(angle);
        if (this.safe(px, py, level)) return [px, py];
      }
    }
    return null;
  }
}
