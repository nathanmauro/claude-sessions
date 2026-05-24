import type { DashboardResponse } from "../api";
import { RangePicker } from "./RangePicker";
import { UsageBar } from "./UsageBar";
import "../styles/components/topbar.css";

interface Props {
  data: DashboardResponse | undefined;
}

export function TopBar({ data }: Props) {
  return (
    <header className="top">
      <div className="brand">
        <span className="brand-dot" aria-hidden="true" />
        <h1>
          agent<span className="brand-sep">·</span>sessions
        </h1>
      </div>
      <RangePicker />
      {data && <UsageBar data={data} />}
    </header>
  );
}
