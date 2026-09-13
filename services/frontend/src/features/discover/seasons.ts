/** Season 0 is Sonarr's specials bucket, which reads badly as "Season 0". */
export const seasonLabelKey = (seasonNumber: number) =>
  seasonNumber <= 0 ? 'discover.seasons.specials' : 'discover.seasons.season';
