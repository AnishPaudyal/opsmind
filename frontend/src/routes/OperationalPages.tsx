import { useState, type ReactNode } from "react";
import { useForm } from "react-hook-form";
import { Link, useParams } from "react-router-dom";

import { ApiError } from "../api/errors";
import { hasPresentationRole } from "../auth/roles";
import { useAuth } from "../auth/context";
import { Button } from "../components/Button";
import { FormField } from "../components/FormField";
import { PageHeader } from "../components/PageHeader";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import {
  useAppendDemand,
  useApproveRecommendation,
  useAuditHistory,
  useCreateProduct,
  useDemand,
  useExposure,
  useForecast,
  useInventory,
  usePersistRecommendation,
  useProduct,
  useProducts,
  useRecommendation,
  useRecommendations,
  useRejectRecommendation,
  useReorder,
  useSetInventory,
  type ProductCreate,
  type RecommendationFilters,
  type ReviewStatus,
} from "../features/operations";

function errorMessage(error: unknown): ReactNode {
  const requestId = error instanceof ApiError ? error.requestId : undefined;
  return (
    <>
      <p>
        {error instanceof Error
          ? error.message
          : "OpsMind could not complete the request."}
      </p>
      {requestId ? (
        <p>
          Request ID: <code>{requestId}</code>
        </p>
      ) : null}
    </>
  );
}

function RequestError({
  error,
  title,
}: {
  readonly error: unknown;
  readonly title?: string;
}) {
  return <ErrorState {...(title ? { title } : {})}>{errorMessage(error)}</ErrorState>;
}

function Panel({
  children,
  title,
}: {
  readonly children: ReactNode;
  readonly title: string;
}) {
  return (
    <section className="data-panel">
      <h2>{title}</h2>
      {children}
    </section>
  );
}

function Status({ value }: { readonly value: string }) {
  return (
    <span className={`status-badge status-badge--${value}`}>
      {value.replaceAll("_", " ")}
    </span>
  );
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(
    new Date(value),
  );
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

interface ProductFormFields {
  readonly sku: string;
  readonly name: string;
  readonly unit_of_measure: string;
  readonly lead_time_days: number;
}

export function OverviewPage() {
  const products = useProducts();
  const recommendations = useRecommendations();
  const pending = recommendations.data?.filter(
    (review) => review.review_status === "pending_review",
  ).length;
  return (
    <>
      <PageHeader
        description="A bounded operational view of products and persisted decision work."
        eyebrow="Operational overview"
        title="Know what needs attention—and why."
      />
      <div className="metric-grid" aria-label="Operational overview metrics">
        <section className="metric-card">
          <p>Products</p>
          <strong>{products.data?.length ?? "—"}</strong>
        </section>
        <section className="metric-card">
          <p>Pending reviews</p>
          <strong>{pending ?? "—"}</strong>
        </section>
        <section className="metric-card">
          <p>Stored reviews</p>
          <strong>{recommendations.data?.length ?? "—"}</strong>
        </section>
      </div>
      {products.isPending || recommendations.isPending ? (
        <LoadingState label="Loading overview" />
      ) : null}
      {products.error ? (
        <RequestError error={products.error} title="Products are unavailable" />
      ) : null}
      {recommendations.error ? (
        <RequestError error={recommendations.error} title="Reviews are unavailable" />
      ) : null}
      <div className="action-row">
        <Link className="button button--primary" to="/products">
          Open products
        </Link>
        <Link className="button button--secondary" to="/recommendations">
          Review recommendations
        </Link>
      </div>
      <p className="fine-print">
        The overview intentionally uses two collection reads and does not issue
        per-product aggregation requests.
      </p>
    </>
  );
}

export function ProductsPage() {
  const { roles } = useAuth();
  const canWrite = hasPresentationRole(roles, "opsmind.business.write");
  const products = useProducts();
  const create = useCreateProduct();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ProductFormFields>();
  const submit = handleSubmit((values) => {
    const body: ProductCreate = { ...values, is_active: true };
    create.mutate(body, {
      onSuccess: () => {
        reset();
      },
    });
  });
  return (
    <>
      <PageHeader
        description="Browse canonical SKUs and create validated operational records."
        eyebrow="Products"
        title="Operational catalog"
      />
      {canWrite ? (
        <Panel title="Create product">
          <form className="form-grid" onSubmit={(event) => void submit(event)}>
            <FormField
              id="sku"
              label="SKU"
              error={errors.sku?.message}
              registration={register("sku", { required: "SKU is required." })}
            />
            <FormField
              id="name"
              label="Name"
              error={errors.name?.message}
              registration={register("name", { required: "Name is required." })}
            />
            <FormField
              id="unit"
              label="Unit of measure"
              error={errors.unit_of_measure?.message}
              registration={register("unit_of_measure", {
                required: "Unit is required.",
              })}
            />
            <FormField
              id="lead-time"
              label="Lead time (days)"
              type="number"
              min="0"
              error={errors.lead_time_days?.message}
              registration={register("lead_time_days", {
                required: "Lead time is required.",
                valueAsNumber: true,
                min: { value: 0, message: "Lead time cannot be negative." },
              })}
            />
            <Button disabled={create.isPending} type="submit">
              {create.isPending ? "Creating…" : "Create product"}
            </Button>
          </form>
          {create.isSuccess ? (
            <p className="success-message" role="status">
              Product created.
            </p>
          ) : null}
          {create.error ? (
            <RequestError error={create.error} title="Product was not created" />
          ) : null}
        </Panel>
      ) : null}
      {products.isPending ? <LoadingState label="Loading products" /> : null}
      {products.error ? (
        <RequestError error={products.error} title="Products are unavailable" />
      ) : null}
      {products.data?.length === 0 ? (
        <EmptyState title="No products have been created">
          <p>A user with business write permission can create the first product.</p>
        </EmptyState>
      ) : null}
      {products.data && products.data.length > 0 ? (
        <div className="card-list">
          {products.data.map((product) => (
            <article className="record-card" key={product.id}>
              <div>
                <p className="eyebrow">{product.sku}</p>
                <h2>{product.name}</h2>
                <p>
                  {product.unit_of_measure} · {product.lead_time_days} day lead time
                </p>
              </div>
              <Link className="text-link" to={`/products/${product.id}`}>
                Open evidence
              </Link>
            </article>
          ))}
        </div>
      ) : null}
    </>
  );
}

interface InventoryFields {
  readonly onHand: number;
  readonly allocated: number;
}
interface DemandFields {
  readonly demandDate: string;
  readonly quantity: number;
}

export function ProductDetailPage() {
  const productId = useParams().productId ?? "";
  const { roles } = useAuth();
  const canWrite = hasPresentationRole(roles, "opsmind.business.write");
  const [lookback, setLookback] = useState(7);
  const [horizon, setHorizon] = useState(7);
  const [asOfDate, setAsOfDate] = useState("");
  const options = { lookbackObservations: lookback, ...(asOfDate ? { asOfDate } : {}) };
  const product = useProduct(productId);
  const inventory = useInventory(productId);
  const demand = useDemand(productId);
  const forecast = useForecast(productId, { ...options, horizonDays: horizon });
  const exposure = useExposure(productId, options);
  const reorder = useReorder(productId, options);
  const setInventory = useSetInventory(productId);
  const appendDemand = useAppendDemand(productId);
  const persist = usePersistRecommendation(productId);
  const inventoryForm = useForm<InventoryFields>();
  const demandForm = useForm<DemandFields>();
  const submitInventory = inventoryForm.handleSubmit((values) => {
    setInventory.mutate({
      on_hand_quantity: values.onHand,
      allocated_quantity: values.allocated,
    });
  });
  const submitDemand = demandForm.handleSubmit((values) => {
    appendDemand.mutate(
      { observations: [{ demand_date: values.demandDate, quantity: values.quantity }] },
      {
        onSuccess: () => {
          demandForm.reset();
        },
      },
    );
  });

  if (product.isPending) return <LoadingState label="Loading product workspace" />;
  if (product.error)
    return <RequestError error={product.error} title="Product could not be loaded" />;
  return (
    <>
      <PageHeader
        description={`${product.data.sku} · ${product.data.unit_of_measure} · ${String(product.data.lead_time_days)} day lead time`}
        eyebrow="Product workspace"
        title={product.data.name}
      />
      <Panel title="Calculation controls">
        <div className="form-grid compact">
          <FormField
            id="lookback"
            label="Lookback observations"
            type="number"
            min="1"
            max="365"
            value={lookback}
            onChange={(event) => {
              setLookback(Number(event.target.value));
            }}
          />
          <FormField
            id="horizon"
            label="Forecast horizon (days)"
            type="number"
            min="1"
            max="365"
            value={horizon}
            onChange={(event) => {
              setHorizon(Number(event.target.value));
            }}
          />
          <FormField
            id="as-of"
            label="As-of date (optional)"
            type="date"
            value={asOfDate}
            onChange={(event) => {
              setAsOfDate(event.target.value);
            }}
          />
        </div>
      </Panel>
      <div className="section-grid">
        <Panel title="Inventory">
          {inventory.data ? (
            <dl className="evidence-list">
              <div>
                <dt>On hand</dt>
                <dd>{inventory.data.on_hand_quantity}</dd>
              </div>
              <div>
                <dt>Allocated</dt>
                <dd>{inventory.data.allocated_quantity}</dd>
              </div>
              <div>
                <dt>Available</dt>
                <dd>{inventory.data.available_quantity}</dd>
              </div>
            </dl>
          ) : inventory.isPending ? (
            <LoadingState />
          ) : (
            <p>No inventory position is recorded.</p>
          )}
          {canWrite ? (
            <form
              className="form-grid compact"
              onSubmit={(event) => void submitInventory(event)}
            >
              <FormField
                id="on-hand"
                label="On hand"
                type="number"
                min="0"
                registration={inventoryForm.register("onHand", {
                  required: true,
                  valueAsNumber: true,
                  min: 0,
                })}
              />
              <FormField
                id="allocated"
                label="Allocated"
                type="number"
                min="0"
                registration={inventoryForm.register("allocated", {
                  required: true,
                  valueAsNumber: true,
                  min: 0,
                })}
              />
              <Button disabled={setInventory.isPending} type="submit">
                Set inventory
              </Button>
            </form>
          ) : null}
          {setInventory.error ? <RequestError error={setInventory.error} /> : null}
        </Panel>
        <Panel title="Demand history">
          {demand.data?.length ? (
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Quantity</th>
                </tr>
              </thead>
              <tbody>
                {demand.data.map((item) => (
                  <tr key={item.demand_date}>
                    <td>{formatDate(item.demand_date)}</td>
                    <td>{item.quantity}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : demand.isPending ? (
            <LoadingState />
          ) : (
            <p>No demand observations are recorded.</p>
          )}
          {canWrite ? (
            <form
              className="form-grid compact"
              onSubmit={(event) => void submitDemand(event)}
            >
              <FormField
                id="demand-date"
                label="Demand date"
                type="date"
                registration={demandForm.register("demandDate", { required: true })}
              />
              <FormField
                id="demand-quantity"
                label="Quantity"
                type="number"
                min="0"
                registration={demandForm.register("quantity", {
                  required: true,
                  valueAsNumber: true,
                  min: 0,
                })}
              />
              <Button disabled={appendDemand.isPending} type="submit">
                Append observation
              </Button>
            </form>
          ) : null}
          {appendDemand.error ? <RequestError error={appendDemand.error} /> : null}
        </Panel>
        <Panel title="Baseline forecast">
          {forecast.data ? (
            <dl className="evidence-list">
              <div>
                <dt>Method</dt>
                <dd>{forecast.data.method.replaceAll("_", " ")}</dd>
              </div>
              <div>
                <dt>Average daily demand</dt>
                <dd>{forecast.data.average_daily_demand}</dd>
              </div>
              <div>
                <dt>{forecast.data.horizon_days}-day forecast</dt>
                <dd>{forecast.data.forecast_quantity}</dd>
              </div>
              <div>
                <dt>Evidence</dt>
                <dd>
                  {forecast.data.observations_used} observations through{" "}
                  {formatDate(forecast.data.as_of_date)}
                </dd>
              </div>
            </dl>
          ) : forecast.isPending ? (
            <LoadingState />
          ) : (
            <p>Forecast requires eligible demand history.</p>
          )}
        </Panel>
        <Panel title="Stockout exposure">
          {exposure.data ? (
            <dl className="evidence-list">
              <div>
                <dt>Status</dt>
                <dd>
                  <Status value={exposure.data.status} />
                </dd>
              </div>
              <div>
                <dt>Projected balance</dt>
                <dd>{exposure.data.projected_inventory_balance}</dd>
              </div>
              <div>
                <dt>Projected shortage</dt>
                <dd>{exposure.data.projected_shortage_quantity}</dd>
              </div>
            </dl>
          ) : exposure.isPending ? (
            <LoadingState />
          ) : (
            <p>Exposure requires inventory and demand evidence.</p>
          )}
        </Panel>
        <Panel title="Calculated reorder recommendation">
          {reorder.data ? (
            <>
              <dl className="evidence-list">
                <div>
                  <dt>Status</dt>
                  <dd>
                    <Status value={reorder.data.recommendation_status} />
                  </dd>
                </div>
                <div>
                  <dt>Recommended quantity</dt>
                  <dd>
                    {reorder.data.recommended_reorder_quantity}{" "}
                    {reorder.data.unit_of_measure}
                  </dd>
                </div>
                <div>
                  <dt>Policy</dt>
                  <dd>{reorder.data.recommendation_policy.replaceAll("_", " ")}</dd>
                </div>
              </dl>
              <p className="fine-print">
                This calculation does not place an external order.
              </p>
              {canWrite && reorder.data.recommended_reorder_quantity > 0 ? (
                <Button
                  disabled={persist.isPending}
                  onClick={() => {
                    persist.mutate(options);
                  }}
                >
                  {persist.isPending ? "Storing…" : "Persist for review"}
                </Button>
              ) : null}
            </>
          ) : reorder.isPending ? (
            <LoadingState />
          ) : (
            <p>A recommendation requires complete inventory and demand evidence.</p>
          )}
          {persist.data ? (
            <p className="success-message" role="status">
              Stored for review.{" "}
              <Link to={`/recommendations/${persist.data.recommendation_id}`}>
                Open review
              </Link>
            </p>
          ) : null}
          {persist.error ? <RequestError error={persist.error} /> : null}
        </Panel>
      </div>
    </>
  );
}

export function RecommendationsPage() {
  const [productId, setProductId] = useState("");
  const [status, setStatus] = useState<ReviewStatus | "">("");
  const filters: RecommendationFilters = {
    ...(productId ? { productId } : {}),
    ...(status ? { reviewStatus: status } : {}),
  };
  const reviews = useRecommendations(filters);
  return (
    <>
      <PageHeader
        description="Reconstruct durable decision work from stored recommendation snapshots."
        eyebrow="Recommendations"
        title="Decision review queue"
      />
      <Panel title="Exact filters">
        <div className="form-grid compact">
          <FormField
            id="review-product"
            label="Product ID"
            value={productId}
            onChange={(event) => {
              setProductId(event.target.value);
            }}
          />
          <div className="form-field">
            <label htmlFor="review-status">Review status</label>
            <select
              id="review-status"
              value={status}
              onChange={(event) => {
                setStatus(event.target.value as ReviewStatus | "");
              }}
            >
              <option value="">All statuses</option>
              <option value="pending_review">Pending review</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
            </select>
          </div>
        </div>
      </Panel>
      {reviews.isPending ? <LoadingState label="Loading recommendation queue" /> : null}
      {reviews.error ? (
        <RequestError
          error={reviews.error}
          title="Recommendation queue is unavailable"
        />
      ) : null}
      {reviews.data?.length === 0 ? (
        <EmptyState title="No reviews match these filters">
          <p>
            Persist an actionable product recommendation or change the exact filters.
          </p>
        </EmptyState>
      ) : null}
      {reviews.data && reviews.data.length > 0 ? (
        <div className="card-list">
          {reviews.data.map((review) => (
            <article className="record-card" key={review.recommendation_id}>
              <div>
                <p className="eyebrow">{formatDateTime(review.created_at)}</p>
                <h2>
                  {review.recommendation.recommended_reorder_quantity}{" "}
                  {review.recommendation.unit_of_measure}
                </h2>
                <p>
                  Product <code>{review.recommendation.product_id}</code>
                </p>
                <Status value={review.review_status} />
              </div>
              <Link
                className="text-link"
                to={`/recommendations/${review.recommendation_id}`}
              >
                Review evidence
              </Link>
            </article>
          ))}
        </div>
      ) : null}
    </>
  );
}

interface ApprovalFields {
  readonly approvedQuantity?: number;
  readonly note?: string;
}
interface RejectionFields {
  readonly reason: string;
}

export function RecommendationDetailPage() {
  const recommendationId = useParams().recommendationId ?? "";
  const { roles } = useAuth();
  const canDecide = hasPresentationRole(roles, "opsmind.recommendation.decide");
  const review = useRecommendation(recommendationId);
  const audit = useAuditHistory(recommendationId);
  const approve = useApproveRecommendation(recommendationId);
  const reject = useRejectRecommendation(recommendationId);
  const approvalForm = useForm<ApprovalFields>();
  const rejectionForm = useForm<RejectionFields>();
  const submitApproval = approvalForm.handleSubmit((values) => {
    approve.mutate({
      ...(Number.isFinite(values.approvedQuantity)
        ? { approved_quantity: values.approvedQuantity }
        : {}),
      ...(values.note ? { note: values.note } : {}),
    });
  });
  const submitRejection = rejectionForm.handleSubmit((values) => {
    reject.mutate({ reason: values.reason });
  });
  if (review.isPending) return <LoadingState label="Loading recommendation evidence" />;
  if (review.error)
    return (
      <RequestError error={review.error} title="Recommendation could not be loaded" />
    );
  const evidence = review.data.recommendation;
  return (
    <>
      <PageHeader
        description="Immutable calculation evidence, trusted decisions, and ordered audit history."
        eyebrow="Recommendation review"
        title="Decision evidence"
      />
      <div className="section-grid">
        <Panel title="Stored snapshot">
          <Status value={review.data.review_status} />
          <dl className="evidence-list">
            <div>
              <dt>Recommendation</dt>
              <dd>
                {evidence.recommended_reorder_quantity} {evidence.unit_of_measure}
              </dd>
            </div>
            <div>
              <dt>Product</dt>
              <dd>
                <Link to={`/products/${evidence.product_id}`}>
                  {evidence.product_id}
                </Link>
              </dd>
            </div>
            <div>
              <dt>Created</dt>
              <dd>{formatDateTime(review.data.created_at)}</dd>
            </div>
            <div>
              <dt>Forecast evidence</dt>
              <dd>
                {evidence.observations_used} observations;{" "}
                {evidence.average_daily_demand}/day
              </dd>
            </div>
            <div>
              <dt>Projected shortage</dt>
              <dd>{evidence.projected_shortage_quantity}</dd>
            </div>
          </dl>
        </Panel>
        <Panel title="Decision">
          {review.data.decision ? (
            <dl className="evidence-list">
              <div>
                <dt>Decision</dt>
                <dd>{review.data.decision.decision_type}</dd>
              </div>
              <div>
                <dt>Trusted principal</dt>
                <dd>{review.data.decision.decided_by}</dd>
              </div>
              <div>
                <dt>When</dt>
                <dd>{formatDateTime(review.data.decision.decided_at)}</dd>
              </div>
              <div>
                <dt>Note</dt>
                <dd>{review.data.decision.note ?? "—"}</dd>
              </div>
            </dl>
          ) : canDecide ? (
            <div className="decision-grid">
              <form onSubmit={(event) => void submitApproval(event)}>
                <h3>Approve</h3>
                <FormField
                  id="approved-quantity"
                  label="Approved quantity (optional)"
                  type="number"
                  min="1"
                  registration={approvalForm.register("approvedQuantity", {
                    valueAsNumber: true,
                    min: 1,
                  })}
                />
                <FormField
                  id="approval-note"
                  label="Note (optional)"
                  registration={approvalForm.register("note")}
                />
                <Button disabled={approve.isPending || reject.isPending} type="submit">
                  Approve
                </Button>
              </form>
              <form onSubmit={(event) => void submitRejection(event)}>
                <h3>Reject</h3>
                <FormField
                  id="rejection-reason"
                  label="Reason"
                  error={rejectionForm.formState.errors.reason?.message}
                  registration={rejectionForm.register("reason", {
                    required: "A reason is required.",
                  })}
                />
                <Button
                  disabled={approve.isPending || reject.isPending}
                  type="submit"
                  variant="secondary"
                >
                  Reject
                </Button>
              </form>
            </div>
          ) : (
            <p>Decision controls require recommendation decide permission.</p>
          )}
          {approve.error ? <RequestError error={approve.error} /> : null}
          {reject.error ? <RequestError error={reject.error} /> : null}
        </Panel>
      </div>
      <Panel title="Audit history">
        {audit.isPending ? <LoadingState /> : null}
        {audit.error ? <RequestError error={audit.error} /> : null}
        {audit.data ? (
          <ol className="timeline">
            {audit.data.events.map((event) => (
              <li key={event.event_id}>
                <strong>{event.event_type.replaceAll("_", " ")}</strong>
                <span>
                  {formatDateTime(event.occurred_at)} · {event.actor ?? "system"}
                </span>
                {event.note ? <p>{event.note}</p> : null}
              </li>
            ))}
          </ol>
        ) : null}
      </Panel>
    </>
  );
}
