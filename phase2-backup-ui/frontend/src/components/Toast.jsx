export default function Toast({ toast }) {
  return (
    <div
      className={"mem-toast" + (toast ? " show" : "")}
      dangerouslySetInnerHTML={toast ? { __html: toast.html } : undefined}
    />
  );
}