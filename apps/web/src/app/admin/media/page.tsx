import { redirect } from 'next/navigation';

/** Media library is embedded in Compose; keep a friendly redirect. */
export default function MediaLibraryPage() {
  redirect('/admin/compose');
}
