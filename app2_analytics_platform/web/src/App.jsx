import { Routes, Route } from "react-router-dom";
import Shell from "./components/Shell";
import Overview from "./pages/Overview";
import GA4 from "./pages/GA4";
import Ask from "./pages/Ask";
import Predictions from "./pages/Predictions";
import Reports from "./pages/Reports";
import Explorer from "./pages/Explorer";

export default function App() {
  return (
    <Shell>
      <Routes>
        <Route path="/" element={<Overview />} />
        <Route path="/ga4" element={<GA4 />} />
        <Route path="/ask" element={<Ask />} />
        <Route path="/predictions" element={<Predictions />} />
        <Route path="/reports" element={<Reports />} />
        <Route path="/explorer" element={<Explorer />} />
      </Routes>
    </Shell>
  );
}
