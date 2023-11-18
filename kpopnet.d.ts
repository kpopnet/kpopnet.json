export interface Idol {
  // required
  id: string;
  name: string;
  name_original: string;
  real_name: string;
  real_name_original: string;
  birth_date: string;
  urls: string[];
  // optional
  name_alias: string | null;
  debut_date: string | null;
  height: number | null;
  weight: number | null;
  thumb_url: string | null;
  // references
  groups: string[];
}

export interface GroupMember {
  idol_id: string;
  current: boolean;
  roles: string | null;
}

export interface Group {
  // required
  id: string;
  name: string;
  name_original: string;
  agency_name: string;
  urls: string[];
  // optional
  name_alias: string | null;
  debut_date: string | null;
  disband_date: string | null;
  thumb_url: string | null;
  // references
  members: GroupMember[];
  parent_id: string | null;
}

export interface Profiles {
  groups: Group[];
  idols: Idol[];
}

declare const profiles: Profiles;
export default profiles;
