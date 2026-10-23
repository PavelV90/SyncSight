/** How a list view asks the app to open a company profile. */
export type OpenOptions = { healthOnly?: boolean; noticeId?: string };
export type OpenCompany = (uid: string, options?: OpenOptions) => void;
export type ListViewProps = { onOpenCompany: OpenCompany; openedUid: string | null };
