import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { vmsApi } from "@/api/vms";
import NoVNCViewer from "@/components/console/NoVNCViewer";
import { useVMActivityHeartbeat } from "@/hooks/useVMActivityHeartbeat";

export default function ConsolePage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  useVMActivityHeartbeat(sessionId ?? null);

  const { data: session } = useQuery({
    queryKey: ["vms", "mine"],
    queryFn: vmsApi.getMine,
    refetchInterval: 5000,
  });

  if (!session?.console_url) {
    return <p className="text-gray-500">Waiting for console to become available…</p>;
  }

  return (
    <div className="h-[80vh]">
      <NoVNCViewer consoleUrl={session.console_url} />
    </div>
  );
}
