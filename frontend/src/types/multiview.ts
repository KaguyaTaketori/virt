export type GroupSelection =
  | { kind: 'favorites' }
  | { kind: 'org'; orgId: number }
  | null