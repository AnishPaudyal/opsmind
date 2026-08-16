import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import { App } from "../App";
import { publicConfig } from "../test/config-fixture";
import { FakeAuthService } from "../test/fake-auth";

const apiBase = publicConfig.apiBaseUrl;
const product = {
  id: "10000000-0000-0000-0000-000000000001",
  sku: "SENSOR-001",
  name: "Temperature Sensor",
  unit_of_measure: "each",
  lead_time_days: 5,
  is_active: true,
};
const recommendation = {
  product_id: product.id,
  unit_of_measure: "each",
  recommendation_policy: "projected_shortage_ceiling",
  recommendation_status: "reorder_recommended",
  forecast_method: "simple_mean",
  as_of_date: "2026-08-01",
  lookback_observations_requested: 7,
  observations_used: 3,
  training_start_date: "2026-07-30",
  training_end_date: "2026-08-01",
  average_daily_demand: 4,
  lead_time_days: 5,
  on_hand_quantity: 5,
  allocated_quantity: 2,
  available_inventory: 3,
  forecasted_lead_time_demand: 20,
  projected_inventory_balance: -17,
  projected_shortage_quantity: 17,
  recommended_reorder_quantity: 17,
};
const review = {
  recommendation_id: "20000000-0000-0000-0000-000000000001",
  recommendation,
  review_status: "pending_review",
  created_at: "2026-08-01T12:00:00Z",
  decision: null,
};

const server = setupServer();

beforeAll(() => {
  server.listen({ onUnhandledRequest: "error" });
});
afterEach(() => {
  server.resetHandlers();
});
afterAll(() => {
  server.close();
});

function renderRoute(
  path: string,
  roles: ConstructorParameters<typeof FakeAuthService>[1] = ["opsmind.business.read"],
) {
  window.history.replaceState(null, "", path);
  return render(
    <App
      authService={new FakeAuthService("authenticated", roles)}
      config={publicConfig}
    />,
  );
}

describe("operational product workflow", () => {
  it("lists products from the typed API", async () => {
    server.use(
      http.get(`${apiBase}/api/v1/products`, () => HttpResponse.json([product])),
    );
    renderRoute("/products");
    expect(await screen.findByRole("heading", { name: product.name })).toBeVisible();
    expect(screen.getByText(product.sku)).toBeVisible();
  });

  it("shows a truthful empty state and hides write controls without the role", async () => {
    server.use(http.get(`${apiBase}/api/v1/products`, () => HttpResponse.json([])));
    renderRoute("/products");
    expect(
      await screen.findByRole("heading", { name: "No products have been created" }),
    ).toBeVisible();
    expect(
      screen.queryByRole("heading", { name: "Create product" }),
    ).not.toBeInTheDocument();
  });

  it("creates a product and refetches the collection", async () => {
    let products = [] as (typeof product)[];
    server.use(
      http.get(`${apiBase}/api/v1/products`, () => HttpResponse.json(products)),
      http.post(`${apiBase}/api/v1/products`, async ({ request }) => {
        const body = (await request.json()) as Record<string, unknown>;
        expect(body.sku).toBe("sensor-001");
        products = [product];
        return HttpResponse.json(product, { status: 201 });
      }),
    );
    const user = userEvent.setup();
    renderRoute("/products", ["opsmind.business.read", "opsmind.business.write"]);
    await user.type(screen.getByLabelText("SKU"), "sensor-001");
    await user.type(screen.getByLabelText("Name"), product.name);
    await user.type(screen.getByLabelText("Unit of measure"), "each");
    await user.type(screen.getByLabelText("Lead time (days)"), "5");
    await user.click(screen.getByRole("button", { name: "Create product" }));
    expect(await screen.findByText("Product created.")).toBeVisible();
    expect(await screen.findByRole("heading", { name: product.name })).toBeVisible();
  });

  it("validates required product fields before sending a write", async () => {
    const create = vi.fn(() => HttpResponse.json(product, { status: 201 }));
    server.use(
      http.get(`${apiBase}/api/v1/products`, () => HttpResponse.json([])),
      http.post(`${apiBase}/api/v1/products`, create),
    );
    const user = userEvent.setup();
    renderRoute("/products", ["opsmind.business.read", "opsmind.business.write"]);
    await user.click(screen.getByRole("button", { name: "Create product" }));
    expect(await screen.findByText("SKU is required.")).toBeVisible();
    expect(screen.getByText("Name is required.")).toBeVisible();
    expect(create).not.toHaveBeenCalled();
  });

  it("surfaces a duplicate SKU conflict and request ID", async () => {
    server.use(
      http.get(`${apiBase}/api/v1/products`, () => HttpResponse.json([])),
      http.post(`${apiBase}/api/v1/products`, () =>
        HttpResponse.json(
          { detail: "A product with SKU 'SENSOR-001' already exists." },
          { status: 409, headers: { "X-Request-ID": "duplicate-request" } },
        ),
      ),
    );
    const user = userEvent.setup();
    renderRoute("/products", ["opsmind.business.read", "opsmind.business.write"]);
    await user.type(screen.getByLabelText("SKU"), "SENSOR-001");
    await user.type(screen.getByLabelText("Name"), product.name);
    await user.type(screen.getByLabelText("Unit of measure"), "each");
    await user.type(screen.getByLabelText("Lead time (days)"), "5");
    await user.click(screen.getByRole("button", { name: "Create product" }));
    expect(await screen.findByText(/already exists/i)).toBeVisible();
    expect(screen.getByText(/duplicate-request/)).toBeVisible();
  });

  it("loads and mutates the complete product evidence workflow", async () => {
    const inventory = {
      product_id: product.id,
      on_hand_quantity: 5,
      allocated_quantity: 2,
      available_quantity: 3,
    };
    const demand = [{ product_id: product.id, demand_date: "2026-08-01", quantity: 4 }];
    const calls = { inventory: 0, demand: 0, persisted: 0 };
    server.use(
      http.get(`${apiBase}/api/v1/products/${product.id}`, () =>
        HttpResponse.json(product),
      ),
      http.get(`${apiBase}/api/v1/products/${product.id}/inventory`, () =>
        HttpResponse.json(inventory),
      ),
      http.put(`${apiBase}/api/v1/products/${product.id}/inventory`, () => {
        calls.inventory += 1;
        return HttpResponse.json(inventory);
      }),
      http.get(`${apiBase}/api/v1/products/${product.id}/demand`, () =>
        HttpResponse.json(demand),
      ),
      http.post(`${apiBase}/api/v1/products/${product.id}/demand`, () => {
        calls.demand += 1;
        return HttpResponse.json(demand, { status: 201 });
      }),
      http.get(`${apiBase}/api/v1/products/${product.id}/forecast`, () =>
        HttpResponse.json({
          product_id: product.id,
          method: "simple_mean",
          as_of_date: "2026-08-01",
          lookback_observations_requested: 7,
          observations_used: 1,
          training_start_date: "2026-08-01",
          training_end_date: "2026-08-01",
          average_daily_demand: 4,
          horizon_days: 7,
          forecast_quantity: 28,
        }),
      ),
      http.get(`${apiBase}/api/v1/products/${product.id}/stockout-exposure`, () =>
        HttpResponse.json({ ...recommendation, status: "stockout_projected" }),
      ),
      http.get(`${apiBase}/api/v1/products/${product.id}/reorder-recommendation`, () =>
        HttpResponse.json(recommendation),
      ),
      http.post(
        `${apiBase}/api/v1/products/${product.id}/reorder-recommendations`,
        () => {
          calls.persisted += 1;
          return HttpResponse.json(review, { status: 201 });
        },
      ),
      http.get(`${apiBase}/api/v1/reorder-recommendations`, () =>
        HttpResponse.json([review]),
      ),
    );
    const user = userEvent.setup();
    renderRoute(`/products/${product.id}`, [
      "opsmind.business.read",
      "opsmind.business.write",
    ]);
    expect(await screen.findByRole("heading", { name: product.name })).toBeVisible();
    expect(await screen.findByText("simple mean")).toBeVisible();
    expect(screen.getByText("28")).toBeVisible();
    expect(screen.getByText("17 each")).toBeVisible();

    await user.type(screen.getByLabelText("On hand"), "5");
    await user.type(screen.getByLabelText("Allocated"), "2");
    await user.click(screen.getByRole("button", { name: "Set inventory" }));
    await waitFor(() => {
      expect(calls.inventory).toBe(1);
    });

    await user.type(screen.getByLabelText("Demand date"), "2026-08-02");
    await user.type(screen.getByLabelText("Quantity"), "3");
    await user.click(screen.getByRole("button", { name: "Append observation" }));
    await waitFor(() => {
      expect(calls.demand).toBe(1);
    });

    await user.click(screen.getByRole("button", { name: "Persist for review" }));
    expect(await screen.findByText(/Stored for review/)).toBeVisible();
    expect(calls.persisted).toBe(1);
  });

  it("shows bounded missing-evidence states without write controls", async () => {
    server.use(
      http.get(`${apiBase}/api/v1/products/${product.id}`, () =>
        HttpResponse.json(product),
      ),
      http.get(`${apiBase}/api/v1/products/${product.id}/inventory`, () =>
        HttpResponse.json({ detail: "Inventory not found" }, { status: 404 }),
      ),
      http.get(`${apiBase}/api/v1/products/${product.id}/demand`, () =>
        HttpResponse.json([]),
      ),
      http.get(`${apiBase}/api/v1/products/${product.id}/forecast`, () =>
        HttpResponse.json({ detail: "Insufficient history" }, { status: 422 }),
      ),
      http.get(`${apiBase}/api/v1/products/${product.id}/stockout-exposure`, () =>
        HttpResponse.json({ detail: "Inventory not found" }, { status: 404 }),
      ),
      http.get(`${apiBase}/api/v1/products/${product.id}/reorder-recommendation`, () =>
        HttpResponse.json({ detail: "Inventory not found" }, { status: 404 }),
      ),
    );
    renderRoute(`/products/${product.id}`);
    expect(await screen.findByText("No inventory position is recorded.")).toBeVisible();
    expect(screen.getByText("No demand observations are recorded.")).toBeVisible();
    expect(screen.getByText(/Forecast requires eligible/)).toBeVisible();
    expect(
      screen.queryByRole("button", { name: "Set inventory" }),
    ).not.toBeInTheDocument();
  });
});

describe("persisted recommendation workflow", () => {
  it("shows an empty persisted queue without fabricating review IDs", async () => {
    server.use(
      http.get(`${apiBase}/api/v1/reorder-recommendations`, () =>
        HttpResponse.json([]),
      ),
    );
    renderRoute("/recommendations");
    expect(
      await screen.findByRole("heading", {
        name: "No reviews match these filters",
      }),
    ).toBeVisible();
  });

  it("reconstructs the queue and sends exact filters", async () => {
    const requests: URL[] = [];
    server.use(
      http.get(`${apiBase}/api/v1/reorder-recommendations`, ({ request }) => {
        requests.push(new URL(request.url));
        return HttpResponse.json([review]);
      }),
    );
    const user = userEvent.setup();
    renderRoute("/recommendations");
    expect(await screen.findByRole("heading", { name: "17 each" })).toBeVisible();
    await user.selectOptions(screen.getByLabelText("Review status"), "pending_review");
    await waitFor(() => {
      expect(requests.at(-1)?.searchParams.get("review_status")).toBe("pending_review");
    });
  });

  it("renders immutable evidence and trusted audit attribution", async () => {
    server.use(
      http.get(
        `${apiBase}/api/v1/reorder-recommendations/${review.recommendation_id}`,
        () => HttpResponse.json(review),
      ),
      http.get(
        `${apiBase}/api/v1/reorder-recommendations/${review.recommendation_id}/audit-events`,
        () =>
          HttpResponse.json({
            recommendation_id: review.recommendation_id,
            events: [
              {
                event_id: "30000000-0000-0000-0000-000000000001",
                recommendation_id: review.recommendation_id,
                sequence_number: 1,
                event_type: "review_created",
                occurred_at: review.created_at,
                review_status: "pending_review",
                decision_id: null,
                actor: null,
                recommended_reorder_quantity: 17,
                approved_quantity: null,
                note: null,
              },
            ],
          }),
      ),
    );
    renderRoute(`/recommendations/${review.recommendation_id}`);
    expect(
      await screen.findByRole("heading", { name: "Decision evidence" }),
    ).toBeVisible();
    expect(screen.getByText("17 each")).toBeVisible();
    expect(await screen.findByText(/review created/i)).toBeVisible();
    expect(screen.getByText(/system/)).toBeVisible();
  });

  it("approves once and hides decision controls after terminal state", async () => {
    const terminal = {
      ...review,
      review_status: "approved",
      decision: {
        decision_id: "40000000-0000-0000-0000-000000000001",
        decision_type: "approved",
        decided_by: "operator@example.com",
        decided_at: "2026-08-01T13:00:00Z",
        approved_quantity: 17,
        note: "Reviewed",
      },
    };
    const approve = vi.fn(() => HttpResponse.json(terminal));
    server.use(
      http.get(
        `${apiBase}/api/v1/reorder-recommendations/${review.recommendation_id}`,
        () => HttpResponse.json(review),
      ),
      http.get(
        `${apiBase}/api/v1/reorder-recommendations/${review.recommendation_id}/audit-events`,
        () =>
          HttpResponse.json({
            recommendation_id: review.recommendation_id,
            events: [],
          }),
      ),
      http.post(
        `${apiBase}/api/v1/reorder-recommendations/${review.recommendation_id}/approve`,
        approve,
      ),
      http.get(`${apiBase}/api/v1/reorder-recommendations`, () =>
        HttpResponse.json([terminal]),
      ),
    );
    const user = userEvent.setup();
    renderRoute(`/recommendations/${review.recommendation_id}`, [
      "opsmind.business.read",
      "opsmind.recommendation.decide",
    ]);
    await user.click(await screen.findByRole("button", { name: "Approve" }));
    expect(await screen.findByText("operator@example.com")).toBeVisible();
    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
    expect(approve).toHaveBeenCalledOnce();
  });

  it("rejects with the required reason and shows trusted attribution", async () => {
    const terminal = {
      ...review,
      review_status: "rejected",
      decision: {
        decision_id: "40000000-0000-0000-0000-000000000002",
        decision_type: "rejected",
        decided_by: "operator@example.com",
        decided_at: "2026-08-01T13:00:00Z",
        approved_quantity: null,
        note: "Inbound stock confirmed",
      },
    };
    server.use(
      http.get(
        `${apiBase}/api/v1/reorder-recommendations/${review.recommendation_id}`,
        () => HttpResponse.json(review),
      ),
      http.get(
        `${apiBase}/api/v1/reorder-recommendations/${review.recommendation_id}/audit-events`,
        () =>
          HttpResponse.json({
            recommendation_id: review.recommendation_id,
            events: [],
          }),
      ),
      http.post(
        `${apiBase}/api/v1/reorder-recommendations/${review.recommendation_id}/reject`,
        () => HttpResponse.json(terminal),
      ),
      http.get(`${apiBase}/api/v1/reorder-recommendations`, () =>
        HttpResponse.json([terminal]),
      ),
    );
    const user = userEvent.setup();
    renderRoute(`/recommendations/${review.recommendation_id}`, [
      "opsmind.business.read",
      "opsmind.recommendation.decide",
    ]);
    await user.click(await screen.findByRole("button", { name: "Reject" }));
    expect(await screen.findByText("A reason is required.")).toBeVisible();
    await user.type(screen.getByLabelText("Reason"), "Inbound stock confirmed");
    await user.click(screen.getByRole("button", { name: "Reject" }));
    expect(await screen.findByText("operator@example.com")).toBeVisible();
    expect(screen.getByText("Inbound stock confirmed")).toBeVisible();
  });

  it("surfaces a terminal conflict and never retries the mutation", async () => {
    const conflict = vi.fn(() =>
      HttpResponse.json(
        { detail: "Recommendation is already terminal." },
        { status: 409, headers: { "X-Request-ID": "decision-conflict" } },
      ),
    );
    server.use(
      http.get(
        `${apiBase}/api/v1/reorder-recommendations/${review.recommendation_id}`,
        () => HttpResponse.json(review),
      ),
      http.get(
        `${apiBase}/api/v1/reorder-recommendations/${review.recommendation_id}/audit-events`,
        () =>
          HttpResponse.json({
            recommendation_id: review.recommendation_id,
            events: [],
          }),
      ),
      http.post(
        `${apiBase}/api/v1/reorder-recommendations/${review.recommendation_id}/approve`,
        conflict,
      ),
    );
    const user = userEvent.setup();
    renderRoute(`/recommendations/${review.recommendation_id}`, [
      "opsmind.business.read",
      "opsmind.recommendation.decide",
    ]);
    await user.click(await screen.findByRole("button", { name: "Approve" }));
    expect(await screen.findByText(/already terminal/i)).toBeVisible();
    expect(screen.getByText(/decision-conflict/)).toBeVisible();
    expect(conflict).toHaveBeenCalledOnce();
  });

  it("does not render decision controls without presentation permission", async () => {
    server.use(
      http.get(
        `${apiBase}/api/v1/reorder-recommendations/${review.recommendation_id}`,
        () => HttpResponse.json(review),
      ),
      http.get(
        `${apiBase}/api/v1/reorder-recommendations/${review.recommendation_id}/audit-events`,
        () =>
          HttpResponse.json({
            recommendation_id: review.recommendation_id,
            events: [],
          }),
      ),
    );
    renderRoute(`/recommendations/${review.recommendation_id}`);
    expect(await screen.findByText(/decision controls require/i)).toBeVisible();
    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
  });
});
