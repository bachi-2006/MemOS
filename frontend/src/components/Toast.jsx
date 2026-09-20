export default function Toast({ toast }) {
  return (
    <div
      className={"mem-toast" + (toast ? " show" : "")}
      role="status"
      aria-live="polite"
    >
      {toast ? toast.text : ""}
    </div>
  );
}