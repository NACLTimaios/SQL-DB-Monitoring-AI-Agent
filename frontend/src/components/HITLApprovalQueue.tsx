export default function HITLApprovalQueue() {
  return (
    <div className="fixed bottom-4 right-4 bg-slate-800/50 border border-slate-700/50 rounded-xl p-4 w-96 max-h-96 overflow-y-auto">
      <h3 className="text-lg font-semibold text-white mb-2">Approvals</h3>
      <p className="text-slate-400">Pending action approvals</p>
    </div>
  );
}
