/** Loading placeholder shown while the OS catalogue is fetching, matching
 * OSCard's layout so the page doesn't jump when real cards render in. */
export default function OSCardSkeleton() {
  return (
    <div className="card p-5 flex flex-col gap-3 animate-pulse">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-md bg-gray-200 dark:bg-gray-800" />
        <div className="flex-1">
          <div className="h-3.5 w-24 bg-gray-200 dark:bg-gray-800 rounded" />
          <div className="h-2.5 w-12 bg-gray-200 dark:bg-gray-800 rounded mt-2" />
        </div>
      </div>
      <div className="h-3 w-full bg-gray-200 dark:bg-gray-800 rounded" />
      <div className="h-3 w-3/4 bg-gray-200 dark:bg-gray-800 rounded" />
      <div className="grid grid-cols-2 gap-2 mt-1">
        <div className="h-2.5 bg-gray-200 dark:bg-gray-800 rounded" />
        <div className="h-2.5 bg-gray-200 dark:bg-gray-800 rounded" />
      </div>
      <div className="h-9 w-full bg-gray-200 dark:bg-gray-800 rounded-lg mt-2" />
    </div>
  );
}
