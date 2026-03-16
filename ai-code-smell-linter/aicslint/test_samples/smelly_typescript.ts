// Test sample: TypeScript with AI-generated code smells
// Includes interface pattern only possible in TS

// ── ACS001: Empty catch ─────────────────────────────────────
async function loadUser(id: string): Promise<any> {
  try {
    const res = await fetch(`/api/users/${id}`);
    return await res.json();
  } catch (error) {
    // silently fails
  }
}

// ── ACS002: Catch and rethrow ───────────────────────────────
function parseInput(raw: string): object {
  try {
    return JSON.parse(raw);
  } catch (err) {
    throw err;
  }
}

// ── ACS004: Hardcoded secrets ───────────────────────────────
const API_KEY: string = "sk-live-abcdef123456";
const clientSecret: string = "cs_prod_secret_value_here";

// ── ACS005: Unnecessary abstraction ────────────────────────
// AI loves generating interface + single class pattern in TS
interface IUserRepository {
  findById(id: string): Promise<any>;
  save(user: any): Promise<void>;
  delete(id: string): Promise<void>;
}

class UserRepository implements IUserRepository {
  async findById(id: string): Promise<any> {
    return { id, name: "test" };
  }

  async save(user: any): Promise<void> {
    console.log("saved", user);
  }

  async delete(id: string): Promise<void> {
    console.log("deleted", id);
  }
}
