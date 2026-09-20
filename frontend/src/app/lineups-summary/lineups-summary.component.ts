import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';
import { DecimalPipe, NgFor } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { LineupsService } from '../_services/lineups.service';

@Component({
  selector: 'lineups-summary-component',
  templateUrl: './lineups-summary.component.html',
  styleUrl: './lineups-summary.component.scss',
  imports: [DecimalPipe, NgFor, FormsModule],
})
export class LineupsSummaryComponent implements OnInit {

  private readonly lineupsService = inject(LineupsService);
  private readonly cdr = inject(ChangeDetectorRef);

  lineups: any[] = [];

  lineupSize = 5;

  ngOnInit(): void {
    this.loadLineups();
  }

  loadLineups(): void {
    this.lineupsService.getLineupsLeagueSummary(this.lineupSize).subscribe({
      next: (data) => {
        this.lineups = (data.apiResponse as any[])
          .filter((lineup) =>
            lineup.offensive_possessions >= 10 &&
            lineup.defensive_possessions >= 10
          )
          .sort((a, b) => b.net_rating - a.net_rating)
          .slice(0, 10);
        console.log(this.lineups);
        this.cdr.markForCheck();
      },
      error: (error) => {
        console.error('Error loading lineups:', error);
      },
    });
  }
}