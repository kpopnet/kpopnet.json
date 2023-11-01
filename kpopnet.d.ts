// NOTE(Kagami): Should match with types in kpopnet/items.py!

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
  debut_date: string | null;
  height: number | null;
  weight: number | null;
  // references
  groups: string[];
}

export interface GroupMember {
  id: string;
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
  debut_date: string | null;
  disband_date: string | null;
  // references
  members: GroupMember[];
}

export interface Profiles {
  groups: Group[];
  idols: Idol[];
}

declare const profiles: Profiles;
export default profiles;
