using Microsoft.EntityFrameworkCore;

public sealed class CustomerRepository
{
    private readonly AppDbContext _db;
    public CustomerRepository(AppDbContext db) => _db = db;

    public Task<List<Customer>> GetByStateAsync(string state) =>
        _db.Customers
           .AsNoTracking()
           .Where(c => c.State == state)
           .OrderBy(c => c.Name)
           .ToListAsync();
}
